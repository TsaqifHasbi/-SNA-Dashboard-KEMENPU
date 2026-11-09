"""
Fine-Tuning IndoBERT untuk 9 Kelas Emosi (Valensi Positif, Negatif, Netral)
Model Base: indobenchmark/indobert-base-p1 (124M parameter)
Tugas Akhir: IndoBERT & SNA Intelligence Dashboard

Struktur 9 Emosi:
- Positif : Percaya, Antisipasi, Joy
- Negatif : Jijik, Takut, Sedih, Marah
- Netral  : Surprise, Informatif
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'IndoBERT_SNA_MT_PP', 'data')
MODEL_SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'IndoBERT_SNA_MT_PP', 'models', 'best_indobert_emotion_9')
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

MODEL_NAME = "indobenchmark/indobert-base-p1"
NUM_LABELS = 9

EMOTION_9_CLASSES = [
    'Trust',         # 0: Positif (Trust)
    'Anticipation',  # 1: Positif (Anticipation)
    'Joy',           # 2: Positif (Joy / Senang)
    'Disgust',       # 3: Negatif (Disgust)
    'Fear',          # 4: Negatif (Fear)
    'Sadness',       # 5: Negatif (Sadness)
    'Anger',         # 6: Negatif (Anger)
    'Surprise',      # 7: Netral (Surprise / Terkejut)
    'Neutral'        # 8: Netral (Neutral / Information)
]

LABEL2ID = {name: idx for idx, name in enumerate(EMOTION_9_CLASSES)}
ID2LABEL = {idx: name for idx, name in enumerate(EMOTION_9_CLASSES)}

EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral'
}

def check_dependencies():
    missing = []
    try:
        import torch
    except ImportError:
        missing.append("torch")
    try:
        import transformers
    except ImportError:
        missing.append("transformers")
    try:
        import sklearn
    except ImportError:
        missing.append("scikit-learn")
        
    if missing:
        print("\n" + "=" * 70)
        print("⚠️  LIBRARY MACHINE LEARNING BELUM LENGKAP")
        print("=" * 70)
        print(f"Jalankan: pip install {' '.join(missing)}")
        print("=" * 70 + "\n")
        return False
    return True

def run_training_pipeline(epochs=4, batch_size=16, learning_rate=2e-5, max_length=128):
    if not check_dependencies():
        return
        
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
    from torch.optim import AdamW
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
    import seaborn as sns

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print("=" * 70)
    print("🚀 MEMULAI FINE-TUNING INDOBERT UNTUK 9 EMOSI")
    print(f"Device: {device}")
    if device.type == 'cuda':
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    print("=" * 70)

    # 1. Load Data
    train_file = os.path.join(DATA_DIR, 'train_emotion_9.csv')
    val_file = os.path.join(DATA_DIR, 'val_emotion_9.csv')
    test_file = os.path.join(DATA_DIR, 'test_emotion_9.csv')

    if not os.path.exists(train_file):
        print(f"Generating splits first...")
        from prepare_9_emotions_dataset import load_and_standardize_corpus, generate_balanced_splits
        df = load_and_standardize_corpus()
        generate_balanced_splits(df)

    train_df = pd.read_csv(train_file)
    val_df = pd.read_csv(val_file)
    test_df = pd.read_csv(test_file)

    print(f"\n📊 Data loaded:")
    print(f"  Train : {len(train_df):,} rows")
    print(f"  Val   : {len(val_df):,} rows")
    print(f"  Test  : {len(test_df):,} rows")

    # 2. Tokenizer & Dataset
    print(f"\nLoading Tokenizer: {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    class EmotionDataset(Dataset):
        def __init__(self, texts, labels, tokenizer, max_len):
            self.texts = [str(t) for t in texts]
            self.labels = [int(l) for l in labels]
            self.tokenizer = tokenizer
            self.max_len = max_len

        def __len__(self):
            return len(self.texts)

        def __getitem__(self, idx):
            item = self.tokenizer(
                self.texts[idx],
                truncation=True,
                padding='max_length',
                max_length=self.max_len,
                return_tensors='pt'
            )
            return {
                'input_ids': item['input_ids'].squeeze(0),
                'attention_mask': item['attention_mask'].squeeze(0),
                'labels': torch.tensor(self.labels[idx], dtype=torch.long)
            }

    train_dataset = EmotionDataset(train_df['cleaned_content'], train_df['label'], tokenizer, max_length)
    val_dataset = EmotionDataset(val_df['cleaned_content'], val_df['label'], tokenizer, max_length)
    test_dataset = EmotionDataset(test_df['cleaned_content'], test_df['label'], tokenizer, max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    # 3. Model
    print(f"\nLoading IndoBERT model with {NUM_LABELS} emotion classes...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID
    ).to(device)

    optimizer = AdamW(model.parameters(), lr=learning_rate, eps=1e-8)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # 4. Training Loop
    best_f1 = 0.0
    print(f"\n🏋️ Training {epochs} Epochs...")
    for epoch in range(epochs):
        t0 = time.time()
        model.train()
        train_loss = 0.0

        for step, batch in enumerate(train_loader):
            optimizer.zero_grad()
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            train_loss += loss.item()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            if (step + 1) % 100 == 0 or (step + 1) == len(train_loader):
                print(f"  Ep {epoch+1}/{epochs} | Step {step+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

        avg_train_loss = train_loss / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds, val_targets = [], []

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                val_loss += outputs.loss.item()
                preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
                val_preds.extend(preds)
                val_targets.extend(labels.cpu().numpy())

        avg_val_loss = val_loss / len(val_loader)
        val_acc = accuracy_score(val_targets, val_preds)
        _, _, val_f1, _ = precision_recall_fscore_support(val_targets, val_preds, average='macro', zero_division=0)
        elapsed = time.time() - t0

        print(f"  >> Epoch {epoch+1} Done ({elapsed:.0f}s): TrLoss={avg_train_loss:.4f} | VLoss={avg_val_loss:.4f} | VAcc={val_acc*100:.2f}% | VF1={val_f1*100:.2f}%")

        if val_f1 > best_f1:
            best_f1 = val_f1
            model.save_pretrained(MODEL_SAVE_DIR)
            tokenizer.save_pretrained(MODEL_SAVE_DIR)
            print(f"  ⭐ Checkpoint Terbaik Disimpan! (F1={val_f1*100:.2f}%)")

    # 5. Final Test Evaluation
    print("\n" + "=" * 70)
    print("📈 EVALUASI TEST SET INDOBERT 9 EMOSI (INDEPENDENT DATASET)")
    print("=" * 70)

    best_model = AutoModelForSequenceClassification.from_pretrained(MODEL_SAVE_DIR).to(device)
    best_model.eval()

    test_preds, test_targets = [], []
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = best_model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
            test_preds.extend(preds)
            test_targets.extend(labels.cpu().numpy())

    test_acc = accuracy_score(test_targets, test_preds)
    test_prec, test_rec, test_f1, _ = precision_recall_fscore_support(test_targets, test_preds, average='macro', zero_division=0)
    _, _, test_wf1, _ = precision_recall_fscore_support(test_targets, test_preds, average='weighted', zero_division=0)

    print(f"\n🎯 HASIL AKHIR PENGUJIAN 9 EMOSI:")
    print(f"  Akurasi (Accuracy)  : {test_acc*100:.2f}%")
    print(f"  Macro Precision     : {test_prec*100:.2f}%")
    print(f"  Macro Recall        : {test_rec*100:.2f}%")
    print(f"  Macro F1-Score      : {test_f1*100:.2f}%")
    print(f"  Weighted F1-Score   : {test_wf1*100:.2f}%")
    print("\nLaporan Klasifikasi Per-Kelas:")
    print(classification_report(test_targets, test_preds, target_names=EMOTION_9_CLASSES, zero_division=0))

    # Confusion Matrix 9x9 Plot
    cm = confusion_matrix(test_targets, test_preds)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=EMOTION_9_CLASSES, yticklabels=EMOTION_9_CLASSES, ax=ax)
    ax.set_title(f"Confusion Matrix IndoBERT 9 Emosi (Test Acc = {test_acc*100:.2f}%)", fontsize=13, fontweight='bold')
    ax.set_xlabel("Prediksi Model", fontsize=11)
    ax.set_ylabel("Aktual (Ground Truth)", fontsize=11)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    cm_path = os.path.join(MODEL_SAVE_DIR, 'confusion_matrix_9_emotions.png')
    plt.savefig(cm_path, dpi=300)
    plt.close()
    print(f"📊 Confusion Matrix disimpan di: {cm_path}")

    # Sentiment Mapping Evaluation (Periksa konsistensi hierarki ke 3 Sentimen)
    pred_sentiments = [EMOTION_TO_SENTIMENT[ID2LABEL[p]] for p in test_preds]
    true_sentiments = [EMOTION_TO_SENTIMENT[ID2LABEL[t]] for t in test_targets]
    sent_acc = accuracy_score(true_sentiments, pred_sentiments)
    print(f"\n🔮 Akurasi Sentimen Implisit dari 9 Emosi: {sent_acc*100:.2f}%")

    # Simpan metrics JSON
    metrics = {
        'model_name': MODEL_NAME,
        'task': 'emotion_classification_9_classes',
        'classes': EMOTION_9_CLASSES,
        'label2id': LABEL2ID,
        'id2label': ID2LABEL,
        'emotion_to_sentiment': EMOTION_TO_SENTIMENT,
        'test_accuracy': float(test_acc),
        'macro_precision': float(test_prec),
        'macro_recall': float(test_rec),
        'macro_f1': float(test_f1),
        'weighted_f1': float(test_wf1),
        'implicit_sentiment_accuracy': float(sent_acc),
        'confusion_matrix': cm.tolist()
    }
    metrics_path = os.path.join(MODEL_SAVE_DIR, 'evaluation_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print(f"📝 Metrik evaluasi lengkap tersimpan di: {metrics_path}")

if __name__ == '__main__':
    run_training_pipeline()
