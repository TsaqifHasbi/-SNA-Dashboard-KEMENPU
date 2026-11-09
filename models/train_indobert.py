"""
IndoBERT Fine-Tuning Pipeline for Sentiment Analysis
Model Base: indobenchmark/indobert-base-p1
Output: Best Checkpoint, Evaluasi Lengkap (Accuracy, Precision, Recall, F1, Confusion Matrix)
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

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MODEL_SAVE_DIR = os.path.join(os.path.dirname(__file__), 'best_indobert_sentiment')
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# Model resmi IndoBERT dari IndoBenchmark (Phase 1 Base)
MODEL_NAME = "indobenchmark/indobert-base-p1"
NUM_LABELS = 3
LABEL_NAMES = ['Negatif', 'Netral', 'Positif']

def check_dependencies():
    """Memeriksa ketersediaan library PyTorch & HuggingFace."""
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
        print(f"Untuk menjalankan training IndoBERT, silakan install library berikut:")
        print(f"👉 pip install {' '.join(missing)}")
        print("\nJika menggunakan Google Colab:")
        print("👉 !pip install transformers torch scikit-learn matplotlib seaborn")
        print("=" * 70 + "\n")
        return False
    return True

def run_training_pipeline(epochs=3, batch_size=16, learning_rate=2e-5, max_length=128):
    if not check_dependencies():
        return
    
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
    from torch.optim import AdamW
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🚀 Device yang digunakan untuk Training: {device}")
    if device.type == 'cuda':
        print(f"   GPU Model: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM Tersedia: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("   [INFO] Berjalan pada CPU (Disarankan gunakan Google Colab GPU untuk training penuh).")
        
    # 1. Load Data
    train_path = os.path.join(DATA_DIR, 'train.csv')
    val_path = os.path.join(DATA_DIR, 'val.csv')
    test_path = os.path.join(DATA_DIR, 'test.csv')
    
    if not os.path.exists(train_path):
        print(f"[!] Data latih tidak ditemukan di {train_path}.")
        print("Menjalankan label_training_data.py terlebih dahulu...")
        from label_training_data import prepare_labeled_dataset
        train_df, val_df, test_df = prepare_labeled_dataset()
    else:
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)
        
    print(f"\n📊 Ukuran Dataset:")
    print(f"   - Train: {len(train_df):,} baris")
    print(f"   - Val  : {len(val_df):,} baris")
    print(f"   - Test : {len(test_df):,} baris")
    
    # 2. Inisialisasi Tokenizer
    print(f"\nMemuat Tokenizer IndoBERT ({MODEL_NAME})...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    class SentimentDataset(Dataset):
        def __init__(self, texts, labels, tokenizer, max_len):
            self.texts = texts
            self.labels = labels
            self.tokenizer = tokenizer
            self.max_len = max_len
            
        def __len__(self):
            return len(self.texts)
            
        def __getitem__(self, item):
            text = str(self.texts[item])
            label = self.labels[item]
            
            encoding = self.tokenizer(
                text,
                truncation=True,
                max_length=self.max_len,
                padding='max_length',
                return_tensors='pt'
            )
            
            return {
                'input_ids': encoding['input_ids'].flatten(),
                'attention_mask': encoding['attention_mask'].flatten(),
                'labels': torch.tensor(label, dtype=torch.long)
            }
            
    train_dataset = SentimentDataset(train_df['cleaned_content'].values, train_df['label'].values, tokenizer, max_length)
    val_dataset = SentimentDataset(val_df['cleaned_content'].values, val_df['label'].values, tokenizer, max_length)
    test_dataset = SentimentDataset(test_df['cleaned_content'].values, test_df['label'].values, tokenizer, max_length)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    # 3. Inisialisasi Model IndoBERT
    print(f"Memuat Model IndoBERT ({MODEL_NAME}) untuk {NUM_LABELS} kelas...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS
    )
    model.to(device)
    
    optimizer = AdamW(model.parameters(), lr=learning_rate, eps=1e-8)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps
    )
    
    # 4. Training Loop
    print("\n" + "=" * 70)
    print("🏋️  MEMULAI PROSES TRAINING & FINE-TUNING INDOBERT")
    print(f"   Epochs: {epochs} | Batch Size: {batch_size} | Learning Rate: {learning_rate}")
    print("=" * 70)
    
    best_val_f1 = 0.0
    
    for epoch in range(epochs):
        model.train()
        total_train_loss = 0
        start_time = time.time()
        
        for step, batch in enumerate(train_loader):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            model.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_train_loss += loss.item()
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            
            if (step + 1) % 50 == 0 or (step + 1) == len(train_loader):
                elapsed = time.time() - start_time
                print(f"   Epoch {epoch+1}/{epochs} | Step {step+1}/{len(train_loader)} | Batch Loss: {loss.item():.4f} | Time: {elapsed:.1f}s")
                
        avg_train_loss = total_train_loss / len(train_loader)
        
        # Validasi
        model.eval()
        val_preds, val_trues = [], []
        total_val_loss = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                total_val_loss += outputs.loss.item()
                logits = outputs.logits
                preds = torch.argmax(logits, dim=1).cpu().numpy()
                
                val_preds.extend(preds)
                val_trues.extend(labels.cpu().numpy())
                
        avg_val_loss = total_val_loss / len(val_loader)
        val_acc = accuracy_score(val_trues, val_preds)
        val_prec, val_rec, val_f1, _ = precision_recall_fscore_support(val_trues, val_preds, average='macro')
        
        print(f"\n📈 [Hasil Epoch {epoch+1}]")
        print(f"   Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")
        print(f"   Val Accuracy : {val_acc*100:.2f}%")
        print(f"   Val Precision: {val_prec*100:.2f}%")
        print(f"   Val Recall   : {val_rec*100:.2f}%")
        print(f"   Val F1-Score : {val_f1*100:.2f}%\n")
        
        # Simpan checkpoint terbaik berdasarkan Macro F1
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            print(f"   💾 Model terbaik baru (F1: {val_f1*100:.2f}%)! Menyimpan ke {MODEL_SAVE_DIR}...")
            model.save_pretrained(MODEL_SAVE_DIR)
            tokenizer.save_pretrained(MODEL_SAVE_DIR)
            
    # 5. Evaluasi Akhir pada Test Set
    print("\n" + "=" * 70)
    print("🧪 EVALUASI AKHIR PADA TEST SET (DATA TAK TERLIHAT)")
    print("=" * 70)
    
    # Load best model
    best_model = AutoModelForSequenceClassification.from_pretrained(MODEL_SAVE_DIR).to(device)
    best_model.eval()
    
    test_preds, test_trues = [], []
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            outputs = best_model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
            
            test_preds.extend(preds)
            test_trues.extend(batch['labels'].numpy())
            
    # Hitung metrik lengkap
    acc = accuracy_score(test_trues, test_preds)
    macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(test_trues, test_preds, average='macro')
    weighted_prec, weighted_rec, weighted_f1, _ = precision_recall_fscore_support(test_trues, test_preds, average='weighted')
    
    print(f"\n📊 HASIL METRIK PENGUJIAN AKHIR:")
    print(f"   • Accuracy        : {acc*100:.2f}%")
    print(f"   • Macro Precision : {macro_prec*100:.2f}%")
    print(f"   • Macro Recall    : {macro_rec*100:.2f}%")
    print(f"   • Macro F1-Score  : {macro_f1*100:.2f}%")
    print(f"   • Weighted F1     : {weighted_f1*100:.2f}%")
    
    print("\n📋 Classification Report:")
    report = classification_report(test_trues, test_preds, target_names=LABEL_NAMES)
    print(report)
    
    # Confusion Matrix
    cm = confusion_matrix(test_trues, test_preds)
    print("🔲 Confusion Matrix:")
    print("Prediksi ->   Negatif   Netral   Positif")
    for i, name in enumerate(LABEL_NAMES):
        print(f"Aktual {name:<7}: {cm[i][0]:>7}  {cm[i][1]:>7}  {cm[i][2]:>7}")
        
    # Plot & Simpan Visualisasi Confusion Matrix untuk Bab IV Skripsi
    try:
        import seaborn as sns
        plt.figure(figsize=(7, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=LABEL_NAMES, yticklabels=LABEL_NAMES)
        plt.title(f"Confusion Matrix IndoBERT (Accuracy: {acc*100:.2f}%)", fontsize=12, fontweight='bold', pad=12)
        plt.xlabel("Label Prediksi Model", fontsize=10)
        plt.ylabel("Label Aktual (Ground Truth)", fontsize=10)
        plt.tight_layout()
        cm_plot_path = os.path.join(MODEL_SAVE_DIR, 'confusion_matrix.png')
        plt.savefig(cm_plot_path, dpi=300)
        plt.close()
        print(f"📊 Gambar grafik Confusion Matrix tersimpan ke: {cm_plot_path}")
    except Exception as e:
        print(f"⚠️ Gagal menyimpan grafik confusion matrix: {e}")

    # Simpan metrics report ke JSON
    metrics_summary = {
        'model_name': MODEL_NAME,
        'accuracy': float(acc),
        'macro_precision': float(macro_prec),
        'macro_recall': float(macro_rec),
        'macro_f1': float(macro_f1),
        'weighted_f1': float(weighted_f1),
        'confusion_matrix': cm.tolist(),
        'label_names': LABEL_NAMES
    }
    metrics_path = os.path.join(MODEL_SAVE_DIR, 'evaluation_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=4)
    print(f"\n💾 Laporan evaluasi tersimpan ke: {metrics_path}")
    print("=" * 70)

if __name__ == '__main__':
    run_training_pipeline()
