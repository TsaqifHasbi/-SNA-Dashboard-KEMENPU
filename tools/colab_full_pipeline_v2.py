"""
============================================================================
FULL PIPELINE: Gemini Annotation + IndoBERT V2 Training + Inference
============================================================================
ALL-IN-ONE Google Colab Notebook dengan GPU T4
Mendukung auto-fallback ke 24.000 korpus seimbang jika kuota Gemini habis.

CARA PAKAI:
  1. Buat folder "IndoBERT_SNA" di Google Drive
  2. Upload file berikut ke folder tersebut:
     - gold_standard_sample_1000.csv  (sudah di-generate)
     - master_scraped_corpus.csv      (dari IndoBERT_SNA_MT_PP/data/)
     - enriched_corpus_for_sna.parquet (dari IndoBERT_SNA_MT_PP/data/)
  3. Buka notebook ini di Colab
  4. Runtime -> Change runtime type -> GPU (T4)
  5. Run All (Ctrl + F9)
============================================================================
"""

# =====================================================================
# CELL 1: INSTALL & SETUP
# =====================================================================
# !pip install transformers torch accelerate scikit-learn seaborn pandas pyarrow google-genai networkx -q

# pyrefly: ignore [missing-import]
# pyright: reportMissingImports=false
import os, sys, time, json, re
# pyrefly: ignore [missing-import]
import numpy as np  
import pandas as pd
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt

import torch  # type: ignore
from torch.utils.data import Dataset, DataLoader  # type: ignore
from torch.optim import AdamW  # type: ignore
from transformers import (  # type: ignore
    AutoTokenizer, AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)
from sklearn.model_selection import train_test_split
from google import genai  # type: ignore

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")
if device.type == 'cuda':
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

# =====================================================================
# CELL 2: MOUNT DRIVE & CONFIG
# =====================================================================
# pyrefly: ignore [missing-import]
from google.colab import drive
drive.mount('/content/drive')

DRIVE_DIR = '/content/drive/MyDrive/IndoBERT_SNA'
os.makedirs(DRIVE_DIR, exist_ok=True)

# Daftar API Keys Gemini dari berbagai project di Google AI Studio (https://aistudio.google.com/)
# Semakin banyak project berbeda yang Anda buat, semakin banyak kuota token gratis yang bisa di-rotasi otomatis!
GEMINI_API_KEYS = [
    "YOUR_GEMINI_API_KEY_HERE",
    "YOUR_GEMINI_API_KEY_HERE",
    "YOUR_GEMINI_API_KEY_HERE",
    "YOUR_GEMINI_API_KEY_HERE",
    # 4 API Key Cadangan (Commented):
    # "YOUR_GEMINI_API_KEY_HERE",
    # "YOUR_GEMINI_API_KEY_HERE",
    # "YOUR_GEMINI_API_KEY_HERE",
    # "YOUR_GEMINI_API_KEY_HERE",
]
# Kompatibilitas jika user menggunakan variabel tunggal
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

GOLD_SAMPLE_PATH = os.path.join(DRIVE_DIR, 'gold_standard_sample_1000.csv')
GOLD_ANNOTATED_PATH = os.path.join(DRIVE_DIR, 'gold_standard_annotated_1000.csv')
MASTER_PATH = os.path.join(DRIVE_DIR, 'master_scraped_corpus.csv')
ENRICHED_PATH = os.path.join(DRIVE_DIR, 'enriched_corpus_for_sna.parquet')
CHECKPOINT_PATH = os.path.join(DRIVE_DIR, 'annotation_checkpoint.json')
SENT_DIR = os.path.join(DRIVE_DIR, 'best_indobert_sentiment_v2')
EMO_DIR = os.path.join(DRIVE_DIR, 'best_indobert_emotion')

MODEL_NAME = "indobenchmark/indobert-base-p1"
SENTIMENT_LABELS = ['Negatif', 'Netral', 'Positif']

# 9 EMOTION TAXONOMY (Extended Plutchik - English):
# Positif (3): Trust, Anticipation, Joy
# Negatif (4): Disgust, Fear, Sadness, Anger
# Netral  (2): Surprise, Neutral
EMOTION_9_CLASSES = [
    'Trust',         # 0: Positif (Percaya)
    'Anticipation',  # 1: Positif (Antisipasi)
    'Joy',           # 2: Positif (Joy / Senang)
    'Disgust',       # 3: Negatif (Jijik)
    'Fear',          # 4: Negatif (Takut)
    'Sadness',       # 5: Negatif (Sedih)
    'Anger',         # 6: Negatif (Marah)
    'Surprise',      # 7: Netral (Surprise / Terkejut)
    'Neutral'        # 8: Netral (Neutral / Informatif)
]
EMOTION_LABELS = EMOTION_9_CLASSES
EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral',
    # Fallback jika ada label Indonesia
    'Percaya': 'Positif', 'Antisipasi': 'Positif', 'Senang': 'Positif',
    'Jijik': 'Negatif', 'Takut': 'Negatif', 'Sedih': 'Negatif', 'Marah': 'Negatif',
    'Terkejut': 'Netral', 'Informatif': 'Netral', 'Netral': 'Netral'
}

# =====================================================================
# CELL 3: GEMINI ANNOTATION (Langkah 1 & 2)
# =====================================================================
print("=" * 70)
print("LANGKAH 1: ANOTASI GOLD STANDARD DENGAN GEMINI")
print("=" * 70)

need_annotation = True
gold_df = pd.DataFrame()

if need_annotation:
    # Kumpulkan list API Keys yang valid untuk rotasi otomatis
    if isinstance(GEMINI_API_KEYS, str):
        keys_pool = [GEMINI_API_KEYS]
    elif isinstance(GEMINI_API_KEYS, list):
        keys_pool = [k for k in GEMINI_API_KEYS if k and not k.startswith("AIzaSy...")]
    else:
        keys_pool = [GEMINI_API_KEY] if GEMINI_API_KEY else []

    if not keys_pool:
        print("⚠️ Tidak ada API Key Gemini yang terdeteksi.")
        working_model = None
    else:
        current_key_idx = 0
        client = genai.Client(api_key=keys_pool[current_key_idx])
        print(f"🔑 Terdeteksi {len(keys_pool)} API Key Gemini untuk rotasi otomatis token.")

        # Model yang didukung: prioritaskan 3.8-flash, 3.7-flash, 3.1-flash-lite
        MODELS = ['gemini-3.8-flash', 'gemini-3.7-flash', 'gemini-3.1-flash-lite']
        working_model = None
        for k_i, k_candidate in enumerate(keys_pool):
            test_cli = genai.Client(api_key=k_candidate)
            for m in MODELS:
                try:
                    r = test_cli.models.generate_content(model=m, contents='1+1=?')
                    working_model = m
                    client = test_cli
                    current_key_idx = k_i
                    print(f"  ✅ Model aktif: {m} (Menggunakan API Key #{k_i+1}: {k_candidate[:10]}...)")
                    break
                except Exception as e:
                    continue
            if working_model:
                break

    if not working_model:
        print("⚠️ Tidak ada model Gemini yang tersedia saat ini (kuota habis atau server sibuk).")
        print("Pipeline akan otomatis menggunakan 24.000 korpus seimbang untuk training IndoBERT.")
        gold_df = pd.DataFrame()
    else:
        PROMPT = """Kamu ahli analisis sentimen Bahasa Indonesia untuk kebijakan publik (MBG, Koperasi Desa, Sekolah Rakyat).

Label setiap teks dengan 9 EMOSI (Extended Plutchik - English):
- sentiment: "Positif" / "Netral" / "Negatif"
- emotion: "Trust" / "Anticipation" / "Joy" / "Disgust" / "Fear" / "Sadness" / "Anger" / "Surprise" / "Neutral"
- confidence: 0.0-1.0
- reason: alasan singkat

Panduan 9 Emosi:
- Trust: Percaya, optimis, mendukung, kawal program, kredibel
- Anticipation: Harapan, ekspektasi, menunggu realisasi ke depan
- Joy: Senang, apresiasi, bersyukur, bangga
- Disgust: Jijik, muak, cacing/makanan basi, bau, korupsi memalukan
- Fear: Takut, was-was, khawatir keracunan, cemas anggaran jebol
- Sadness: Sedih, kecewa, miris, prihatin
- Anger: Marah, geram, emosi, kritik keras, menuntut
- Surprise: Kaget, heran, tak terduga, wow, shock
- Neutral: Informatif, berita faktual, pengumuman netral

PENTING - pahami KONTEKS:
- "Tidak gagal, berhasil" = Positif, Joy/Trust
- "Keracunan setelah makan MBG" = Negatif, Fear/Disgust
- "Cacing dalam makanan" = Negatif, Disgust
- "Bagus tapi banyak masalah" = Negatif, Sadness/Anger
- Sarkasme "Terima kasih atas korupsinya" = Negatif, Anger/Disgust

Output JSON array saja tanpa markdown:
[{{"idx":0,"sentiment":"...","emotion":"...","confidence":0.9,"reason":"..."}}]

TEKS:
{texts}"""

        if not os.path.exists(GOLD_SAMPLE_PATH):
            print(f"File sampel {GOLD_SAMPLE_PATH} tidak ditemukan.")
            print("Mencari dari master/enriched...")
            if os.path.exists(ENRICHED_PATH):
                sample_src = pd.read_parquet(ENRICHED_PATH)
            else:
                sample_src = pd.read_csv(MASTER_PATH, low_memory=False)
            df_sample = sample_src.sample(min(1000, len(sample_src)), random_state=42)
        else:
            df_sample = pd.read_csv(GOLD_SAMPLE_PATH)

        print(f"Sampel yang akan dianotasi: {len(df_sample):,}")

        BATCH_SIZE = 10
        batches = [df_sample.iloc[i:i+BATCH_SIZE] for i in range(0, len(df_sample), BATCH_SIZE)]
        total_batches = len(batches)

        done_set = set()
        all_anns = []
        if os.path.exists(CHECKPOINT_PATH):
            try:
                with open(CHECKPOINT_PATH, 'r') as f:
                    cp = json.load(f)
                done_set = set(cp.get('done', []))
                all_anns = cp.get('ann', [])
                print(f"Resume checkpoint: {len(done_set)} batches, {len(all_anns)} anotasi.")
            except:
                pass

        t0 = time.time()

        for bn, bdf in enumerate(batches):
            if bn in done_set:
                continue

            texts = ""
            for i, (_, row) in enumerate(bdf.iterrows()):
                t = str(row['cleaned_content'])[:300].replace('"', "'")
                texts += f'\n[{i}] ({row.get("platform", "web")}/{row.get("topic", "kebijakan")}) "{t}"\n'
            prompt = PROMPT.format(texts=texts)

            results = None
            try:
                r = client.models.generate_content(
                    model=working_model, contents=prompt,
                    config={'temperature': 0.1, 'max_output_tokens': 2048}
                )
                text = r.text.strip()
                if text.startswith('```'):
                    text = '\n'.join(text.split('\n')[1:])
                    if '```' in text: text = text[:text.rfind('```')]
                text = text.strip()
                try:
                    results = json.loads(text)
                except:
                    m = re.search(r'\[.*\]', text, re.DOTALL)
                    if m:
                        try: results = json.loads(m.group())
                        except: pass
            except Exception as e:
                err_msg = str(e)
                print(f"⚠️ Catatan Batch {bn+1}: {err_msg[:90]}")
                # Jika tersedia lebih dari 1 key, otomatis rotasi ke API key berikutnya!
                if len(keys_pool) > 1:
                    current_key_idx = (current_key_idx + 1) % len(keys_pool)
                    next_k = keys_pool[current_key_idx]
                    client = genai.Client(api_key=next_k)
                    print(f"🔄 Otomatis rotasi ke API Key #{current_key_idx+1} ({next_k[:10]}...)...")
                    try:
                        r = client.models.generate_content(
                            model=working_model, contents=prompt,
                            config={'temperature': 0.1, 'max_output_tokens': 2048}
                        )
                        text = r.text.strip()
                        if text.startswith('```'): text = '\n'.join(text.split('\n')[1:])
                        if '```' in text: text = text[:text.rfind('```')]
                        results = json.loads(text.strip())
                    except Exception as e2:
                        pass
                elif '429' in err_msg or 'RESOURCE_EXHAUSTED' in err_msg:
                    print(f"⏳ Rate limit tercapai pada Batch {bn+1}. Istirahat 20 detik...")
                    time.sleep(20)
                    try:
                        r = client.models.generate_content(
                            model=working_model, contents=prompt,
                            config={'temperature': 0.1, 'max_output_tokens': 2048}
                        )
                        text = r.text.strip()
                        if text.startswith('```'): text = '\n'.join(text.split('\n')[1:])
                        if '```' in text: text = text[:text.rfind('```')]
                        results = json.loads(text.strip())
                    except:
                        pass

            # Jika batch ini ada kendala format/filter, JANGAN MACET!
            # Lengkapi otomatis dan LANGSUNG LANJUT KE BATCH BERIKUTNYA
            if not isinstance(results, list):
                results = []

            while len(results) < len(bdf):
                results.append({"sentiment": "Netral", "emotion": "Neutral", "confidence": 0.5, "reason": "auto-filled"})

            emo_clean_map = {
                'Senang': 'Joy', 'Joy': 'Joy',
                'Percaya': 'Trust', 'Trust': 'Trust',
                'Antisipasi': 'Anticipation', 'Anticipation': 'Anticipation',
                'Jijik': 'Disgust', 'Disgust': 'Disgust',
                'Takut': 'Fear', 'Fear': 'Fear',
                'Sedih': 'Sadness', 'Sadness': 'Sadness',
                'Marah': 'Anger', 'Anger': 'Anger',
                'Terkejut': 'Surprise', 'Surprise': 'Surprise',
                'Informatif': 'Neutral', 'Netral': 'Neutral', 'Neutral': 'Neutral'
            }

            for i, (di, row) in enumerate(bdf.iterrows()):
                r = results[i] if i < len(results) and isinstance(results[i], dict) else {}
                sent_val = r.get('sentiment', 'Netral')
                if sent_val not in {'Positif', 'Negatif', 'Netral'}:
                    sent_val = 'Netral'
                raw_emo = str(r.get('emotion', 'Neutral')).strip()
                emo_val = emo_clean_map.get(raw_emo, 'Neutral')
                if emo_val not in EMOTION_9_CLASSES:
                    emo_val = 'Neutral'

                all_anns.append({
                    "original_index": int(di),
                    "platform": row.get('platform', ''), "topic": row.get('topic', ''),
                    "cleaned_content": str(row['cleaned_content'])[:500],
                    "old_sentiment": str(row.get('sentiment_name', '')),
                    "old_emotion": str(row.get('emotion', '')),
                    "gemini_sentiment": sent_val,
                    "gemini_emotion": emo_val,
                    "gemini_confidence": float(r.get('confidence', 0.8)),
                    "gemini_reason": str(r.get('reason', '')),
                })
            done_set.add(bn)

            with open(CHECKPOINT_PATH, 'w') as f:
                json.dump({"done": list(done_set), "ann": all_anns}, f, ensure_ascii=False)

            elapsed = time.time() - t0
            pct = len(done_set) / total_batches * 100
            print(f"  Batch {bn+1}/{total_batches} ({pct:.0f}%) | {elapsed:.0f}s | {len(all_anns)}/1,000 data dianotasi")

            time.sleep(3.5)

        if all_anns:
            gold_df = pd.DataFrame(all_anns)
            gold_df['sentiment_label'] = gold_df['gemini_sentiment'].map({'Negatif': 0, 'Netral': 1, 'Positif': 2})
            gold_df['emotion_label'] = gold_df['gemini_emotion'].map({c: i for i, c in enumerate(EMOTION_9_CLASSES)})
            gold_df.to_csv(GOLD_ANNOTATED_PATH, index=False, encoding='utf-8-sig')
            print(f"\n✅ Anotasi selesai! Disimpan ke: {GOLD_ANNOTATED_PATH}")
            print(f"Total dianotasi: {len(gold_df)}")
        elif os.path.exists(GOLD_ANNOTATED_PATH):
            gold_df = pd.read_csv(GOLD_ANNOTATED_PATH)
            print(f"Memuat anotasi yang sudah ada di Drive: {len(gold_df)} baris")

# =====================================================================
# CELL 4: CROSS-VALIDATE (Langkah 2)
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 2: CROSS-VALIDATE OLD vs GEMINI")
print("=" * 70)

if not gold_df.empty and 'gemini_sentiment' in gold_df.columns and len(gold_df) >= 10:
    ct = pd.crosstab(gold_df['old_sentiment'], gold_df['gemini_sentiment'])
    print("Cross-tabulation (Lama vs Gemini):")
    print(ct.to_string())
    old_acc = (gold_df['old_sentiment'] == gold_df['gemini_sentiment']).mean() * 100
    print(f"\nAkurasi rule-based lama vs Gemini: {old_acc:.1f}%")
else:
    print("Anotasi Gemini terbatas. Mengecek distribusi sentimen korpus:")
    if os.path.exists(ENRICHED_PATH):
        chk = pd.read_parquet(ENRICHED_PATH)
        print(chk['predicted_sentiment'].value_counts().to_string())

# =====================================================================
# CELL 5: PREPARE & TRAIN SENTIMENT MODEL (Langkah 3)
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 3: TRAINING INDOBERT V2 - SENTIMENT")
print("=" * 70)

high_conf = pd.DataFrame()
if not gold_df.empty and 'gemini_confidence' in gold_df.columns:
    high_conf = gold_df[gold_df['gemini_confidence'] >= 0.7].copy()

print("Mempersiapkan dataset 24.000 sampel seimbang (8.000 Positif, 8.000 Netral, 8.000 Negatif) dari korpus...")
if os.path.exists(ENRICHED_PATH):
    src_df = pd.read_parquet(ENRICHED_PATH)
else:
    src_df = pd.read_csv(MASTER_PATH, low_memory=False)

col = 'predicted_sentiment' if 'predicted_sentiment' in src_df.columns else 'sentiment_name'
sub_dfs = []
for s_name, s_lbl in [('Negatif', 0), ('Netral', 1), ('Positif', 2)]:
    match = src_df[src_df[col] == s_name]
    n_take = min(8000, len(match))
    sub = match.sample(n=n_take, random_state=42)[['cleaned_content']].copy()
    sub['sentiment'] = s_name
    sub['label'] = s_lbl
    sub_dfs.append(sub)

train_data_corpus = pd.concat(sub_dfs)
train_data_corpus.columns = ['text', 'sentiment', 'label']

if len(high_conf) >= 100:
    print(f"Menyertakan {len(high_conf):,} data Gold Standard Gemini ke dalam training IndoBERT!")
    gold_train = high_conf[['cleaned_content', 'gemini_sentiment', 'sentiment_label']].copy()
    gold_train.columns = ['text', 'sentiment', 'label']
    train_data = pd.concat([train_data_corpus, gold_train]).sample(frac=1, random_state=42).reset_index(drop=True)
else:
    train_data = train_data_corpus.sample(frac=1, random_state=42).reset_index(drop=True)

# Pembersihan data
train_data = train_data.dropna(subset=['text'])
train_data['text'] = train_data['text'].astype(str)
train_data = train_data[train_data['text'].str.strip().str.len() > 5]

print(f"\n📊 Total data latih IndoBERT: {len(train_data):,} baris")
print(train_data['sentiment'].value_counts().to_string())

# Stratified Split 80/10/10
train_df, temp_df = train_test_split(train_data, test_size=0.2, random_state=42, stratify=train_data['label'])
val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df['label'])
print(f"Split: Train={len(train_df):,}, Val={len(val_df):,}, Test={len(test_df):,}")

class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts, self.labels, self.tokenizer, self.ml = texts, labels, tokenizer, max_length
    def __len__(self): return len(self.texts)
    def __getitem__(self, i):
        enc = self.tokenizer(str(self.texts[i]), truncation=True, max_length=self.ml, padding='max_length', return_tensors='pt')
        return {
            'input_ids': enc['input_ids'].flatten(),
            'attention_mask': enc['attention_mask'].flatten(),
            'labels': torch.tensor(int(self.labels[i]), dtype=torch.long)
        }

EPOCHS = 3
BS = 32
LR = 2e-5
ML = 128

print(f"\nMemuat IndoBERT ({MODEL_NAME})...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
sent_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=3).to(device)

train_loader = DataLoader(TextDataset(train_df['text'].values, train_df['label'].values, tokenizer, ML), batch_size=BS, shuffle=True)
val_loader = DataLoader(TextDataset(val_df['text'].values, val_df['label'].values, tokenizer, ML), batch_size=BS)
test_loader = DataLoader(TextDataset(test_df['text'].values, test_df['label'].values, tokenizer, ML), batch_size=BS)

opt = AdamW(sent_model.parameters(), lr=LR, eps=1e-8)
sched = get_linear_schedule_with_warmup(opt, int(len(train_loader)*EPOCHS*0.1), len(train_loader)*EPOCHS)

SENT_DIR = os.path.join(DRIVE_DIR, 'best_indobert_sentiment_v2')
os.makedirs(SENT_DIR, exist_ok=True)
best_f1 = 0.0

print(f"\n🚀 Memulai Fine-Tuning IndoBERT Sentimen ({EPOCHS} Epochs)...")
for ep in range(EPOCHS):
    sent_model.train()
    total_loss = 0
    t0 = time.time()
    for step, b in enumerate(train_loader):
        ids, mask, lab = b['input_ids'].to(device), b['attention_mask'].to(device), b['labels'].to(device)
        sent_model.zero_grad()
        out = sent_model(input_ids=ids, attention_mask=mask, labels=lab)
        total_loss += out.loss.item()
        out.loss.backward()
        torch.nn.utils.clip_grad_norm_(sent_model.parameters(), 1.0)
        opt.step()
        sched.step()
        if (step+1) % 50 == 0 or (step+1) == len(train_loader):
            print(f"  Ep {ep+1}/{EPOCHS} | Step {step+1}/{len(train_loader)} | Loss: {out.loss.item():.4f}")

    sent_model.eval()
    vp, vt = [], []
    vl = 0
    with torch.no_grad():
        for b in val_loader:
            ids, mask, lab = b['input_ids'].to(device), b['attention_mask'].to(device), b['labels'].to(device)
            out = sent_model(input_ids=ids, attention_mask=mask, labels=lab)
            vl += out.loss.item()
            vp.extend(torch.argmax(out.logits, 1).cpu().numpy())
            vt.extend(lab.cpu().numpy())

    vacc = accuracy_score(vt, vp)
    _, _, vf1, _ = precision_recall_fscore_support(vt, vp, average='macro')
    print(f"  >> Ep {ep+1} Result: TrLoss={total_loss/len(train_loader):.4f} | VLoss={vl/len(val_loader):.4f} | VAcc={vacc*100:.1f}% | VF1={vf1*100:.1f}% ({time.time()-t0:.0f}s)")

    if vf1 > best_f1:
        best_f1 = vf1
        sent_model.save_pretrained(SENT_DIR)
        tokenizer.save_pretrained(SENT_DIR)
        print(f"  ⭐ Checkpoint Terbaik Disimpan! (F1={vf1*100:.1f}%)")

# Test evaluation
best_sent = AutoModelForSequenceClassification.from_pretrained(SENT_DIR).to(device)
best_sent.eval()
tp, tt2 = [], []
with torch.no_grad():
    for b in test_loader:
        out = best_sent(input_ids=b['input_ids'].to(device), attention_mask=b['attention_mask'].to(device))
        tp.extend(torch.argmax(out.logits, 1).cpu().numpy())
        tt2.extend(b['labels'].numpy())

acc = accuracy_score(tt2, tp)
p, r, f, _ = precision_recall_fscore_support(tt2, tp, average='macro')
print(f"\n=======================================================")
print(f"EVALUASI TEST SET INDOBERT SENTIMEN V2:")
print(f"Accuracy : {acc*100:.2f}%")
print(f"Precision: {p*100:.2f}%")
print(f"Recall   : {r*100:.2f}%")
print(f"Macro F1 : {f*100:.2f}%")
print(f"=======================================================")
print(classification_report(tt2, tp, target_names=SENTIMENT_LABELS))

cm = confusion_matrix(tt2, tp)
fig, ax = plt.subplots(figsize=(6,5))
import seaborn as sns
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=SENTIMENT_LABELS, yticklabels=SENTIMENT_LABELS, ax=ax)
ax.set_title(f"IndoBERT Sentiment V2 (Test Acc={acc*100:.1f}%)")
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
plt.tight_layout()
plt.savefig(os.path.join(SENT_DIR, 'confusion_matrix_v2.png'), dpi=300)
plt.show()

with open(os.path.join(SENT_DIR, 'evaluation_metrics.json'), 'w') as fj:
    json.dump({
        'model': MODEL_NAME, 'version': 'v2', 'accuracy': float(acc), 'macro_f1': float(f),
        'confusion_matrix': cm.tolist(), 'labels': SENTIMENT_LABELS
    }, fj, indent=2)

# =====================================================================
# CELL 6: TRAIN EMOTION MODEL (Langkah 5)
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 5: TRAINING INDOBERT - 9 EMOSI (Extended Plutchik - English)")
print("  Positif : Trust, Anticipation, Joy")
print("  Negatif : Disgust, Fear, Sadness, Anger")
print("  Netral  : Surprise, Neutral")
print("=" * 70)

# 9 EMOTION CLASSES (English):
EMOTION_9_CLASSES = [
    'Trust',         # 0: Positif (Percaya)
    'Anticipation',  # 1: Positif (Antisipasi)
    'Joy',           # 2: Positif (Joy / Senang)
    'Disgust',       # 3: Negatif (Jijik)
    'Fear',          # 4: Negatif (Takut)
    'Sadness',       # 5: Negatif (Sedih)
    'Anger',         # 6: Negatif (Marah)
    'Surprise',      # 7: Netral (Surprise / Terkejut)
    'Neutral'        # 8: Netral (Neutral / Informatif)
]
EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral'
}

if os.path.exists(ENRICHED_PATH):
    src_df = pd.read_parquet(ENRICHED_PATH)
else:
    src_df = pd.read_csv(MASTER_PATH, low_memory=False)

# Standarisasi label emosi ke 9 kelas BAHASA INGGRIS
label_rename_en = {
    'Senang': 'Joy', 'Joy': 'Joy',
    'Percaya': 'Trust', 'Trust': 'Trust',
    'Antisipasi': 'Anticipation', 'Anticipation': 'Anticipation',
    'Jijik': 'Disgust', 'Disgust': 'Disgust',
    'Takut': 'Fear', 'Fear': 'Fear',
    'Sedih': 'Sadness', 'Sadness': 'Sadness',
    'Marah': 'Anger', 'Anger': 'Anger',
    'Terkejut': 'Surprise', 'Surprise': 'Surprise',
    'Informatif': 'Neutral', 'Netral': 'Neutral', 'Neutral': 'Neutral'
}
if 'emotion' in src_df.columns:
    src_df['emotion_9'] = src_df['emotion'].replace(label_rename_en)
else:
    src_df['emotion_9'] = 'Neutral'

# Jika korpus di Drive belum memiliki Trust & Anticipation, ekstrak secara otomatis
if 'Trust' not in src_df['emotion_9'].values or 'Anticipation' not in src_df['emotion_9'].values:
    print("Mengekstraksi kelas Trust dan Anticipation dari korpus...")
    ant_pattern = r'semoga|harap|nantikan|menantikan|tunggu|ekspektasi|prospek|rencana|target|ke depan|kedepan|bisa jadi|mudah-mudahan|insya'
    trust_pattern = r'percaya|yakin|dukung|mendukung|amanah|transparan|kredibel|terbukti|sepakat|komitmen|loyal|kawal|mengawal|bukti nyata|terjamin|optimis|mantap betul|setuju'
    surp_pattern = r'kaget|heran|terkejut|tak terduga|tidak disangka|wow|shock|syok|astaga|tiba-tiba|aneh|kok bisa|beneran|ternyata|wah'

    is_joy = src_df['emotion_9'] == 'Joy'
    is_neutral = src_df['emotion_9'] == 'Neutral'

    mask_trust = is_joy & src_df['cleaned_content'].str.contains(trust_pattern, case=False, na=False)
    mask_ant = is_joy & (~mask_trust) & src_df['cleaned_content'].str.contains(ant_pattern, case=False, na=False)
    mask_surp = is_neutral & src_df['cleaned_content'].str.contains(surp_pattern, case=False, na=False)

    src_df.loc[mask_trust, 'emotion_9'] = 'Trust'
    src_df.loc[mask_ant, 'emotion_9'] = 'Anticipation'
    src_df.loc[mask_surp, 'emotion_9'] = 'Surprise'

print("Mempersiapkan dataset 22.500 sampel seimbang murni (2.500 per kelas emosi bahasa Inggris)...")
emo_dfs = []
emo_map = {l: i for i, l in enumerate(EMOTION_9_CLASSES)}

for elabel in EMOTION_9_CLASSES:
    match = src_df[src_df['emotion_9'] == elabel]
    n_take = min(2500, len(match))
    if n_take > 0:
        sub = match.sample(n=n_take, random_state=42)[['cleaned_content']].copy()
        sub['emotion'] = elabel
        sub['label'] = emo_map[elabel]
        emo_dfs.append(sub)


emo_data = pd.concat(emo_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
emo_data.columns = ['text', 'emotion', 'label']

emo_data = emo_data.dropna(subset=['text'])
emo_data['text'] = emo_data['text'].astype(str)
emo_data = emo_data[emo_data['text'].str.strip().str.len() > 10]

print(f"\n📊 Total data training 9 emosi: {len(emo_data):,} baris")
print(emo_data['emotion'].value_counts().to_string())

# Stratified Split: Train 80% (18.000), Val 10% (2.250), Test 10% (2.250)
etrain_df, etemp = train_test_split(emo_data, test_size=0.20, random_state=42, stratify=emo_data['label'])
eval_df, etest_df = train_test_split(etemp, test_size=0.50, random_state=42, stratify=etemp['label'])
print(f"\nSplit 9 Emosi: Train={len(etrain_df):,}, Val={len(eval_df):,}, Test={len(etest_df):,}")

# Inisialisasi Model IndoBERT 9 Kelas
emo_model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, 
    num_labels=9,
    id2label={i: l for i, l in enumerate(EMOTION_9_CLASSES)},
    label2id=emo_map
).to(device)

etrain_loader = DataLoader(TextDataset(etrain_df['text'].values, etrain_df['label'].values, tokenizer, ML), batch_size=BS, shuffle=True)
eval_loader = DataLoader(TextDataset(eval_df['text'].values, eval_df['label'].values, tokenizer, ML), batch_size=BS)
etest_loader = DataLoader(TextDataset(etest_df['text'].values, etest_df['label'].values, tokenizer, ML), batch_size=BS)

eopt = AdamW(emo_model.parameters(), lr=LR, eps=1e-8)
esched = get_linear_schedule_with_warmup(eopt, int(len(etrain_loader)*EPOCHS*0.1), len(etrain_loader)*EPOCHS)

EMO_DIR = os.path.join(DRIVE_DIR, 'best_indobert_emotion')
os.makedirs(EMO_DIR, exist_ok=True)
best_ef1 = 0.0

print(f"\n🚀 Memulai Fine-Tuning IndoBERT 9 Emosi ({EPOCHS} Epochs)...")
for ep in range(EPOCHS):
    emo_model.train()
    total_loss = 0
    t0 = time.time()
    for step, b in enumerate(etrain_loader):
        ids, mask, lab = b['input_ids'].to(device), b['attention_mask'].to(device), b['labels'].to(device)
        emo_model.zero_grad()
        out = emo_model(input_ids=ids, attention_mask=mask, labels=lab)
        total_loss += out.loss.item()
        out.loss.backward()
        torch.nn.utils.clip_grad_norm_(emo_model.parameters(), 1.0)
        eopt.step()
        esched.step()
        if (step+1) % 100 == 0 or (step+1) == len(etrain_loader):
            print(f"  Ep {ep+1}/{EPOCHS} | Step {step+1}/{len(etrain_loader)} | Loss: {out.loss.item():.4f}")

    emo_model.eval()
    ep2, et2 = [], []
    el = 0
    with torch.no_grad():
        for b in eval_loader:
            ids, mask, lab = b['input_ids'].to(device), b['attention_mask'].to(device), b['labels'].to(device)
            out = emo_model(input_ids=ids, attention_mask=mask, labels=lab)
            el += out.loss.item()
            ep2.extend(torch.argmax(out.logits, 1).cpu().numpy())
            et2.extend(lab.cpu().numpy())

    eacc = accuracy_score(et2, ep2)
    _, _, ef1, _ = precision_recall_fscore_support(et2, ep2, average='macro', zero_division=0)
    print(f"  >> Ep {ep+1} Result: TrLoss={total_loss/len(etrain_loader):.4f} | VLoss={el/len(eval_loader):.4f} | VAcc={eacc*100:.1f}% | VF1={ef1*100:.1f}% ({time.time()-t0:.0f}s)")

    if ef1 > best_ef1:
        best_ef1 = ef1
        emo_model.save_pretrained(EMO_DIR)
        tokenizer.save_pretrained(EMO_DIR)
        print(f"  ⭐ Checkpoint 9 Emosi Terbaik Disimpan! (F1={ef1*100:.1f}%)")

# Test evaluation 9 emosi
best_emo = AutoModelForSequenceClassification.from_pretrained(EMO_DIR).to(device)
best_emo.eval()
ep2, et2 = [], []
with torch.no_grad():
    for b in etest_loader:
        out = best_emo(input_ids=b['input_ids'].to(device), attention_mask=b['attention_mask'].to(device))
        ep2.extend(torch.argmax(out.logits, 1).cpu().numpy())
        et2.extend(b['labels'].numpy())

eacc = accuracy_score(et2, ep2)
eprec, erec, ef1, _ = precision_recall_fscore_support(et2, ep2, average='macro', zero_division=0)
print(f"\n=======================================================")
print(f"EVALUASI TEST SET INDOBERT 9 EMOSI (INDEPENDENT DATASET):")
print(f"Accuracy : {eacc*100:.2f}%")
print(f"Precision: {eprec*100:.2f}%")
print(f"Recall   : {erec*100:.2f}%")
print(f"Macro F1 : {ef1*100:.2f}%")
print(f"=======================================================")
labels_9 = list(range(len(EMOTION_9_CLASSES)))
print(classification_report(et2, ep2, labels=labels_9, target_names=EMOTION_9_CLASSES, zero_division=0))

# Confusion Matrix 9x9
cm_emo = confusion_matrix(et2, ep2, labels=labels_9)

fig, ax = plt.subplots(figsize=(10, 8))
import seaborn as sns
sns.heatmap(cm_emo, annot=True, fmt='d', cmap='Blues', xticklabels=EMOTION_9_CLASSES, yticklabels=EMOTION_9_CLASSES, ax=ax)
ax.set_title(f"Confusion Matrix IndoBERT 9 Emosi (Test Acc = {eacc*100:.1f}%)", fontsize=13, fontweight='bold')
ax.set_xlabel("Predicted Emotion")
ax.set_ylabel("Actual Emotion")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(EMO_DIR, 'confusion_matrix_9_emotions.png'), dpi=300)
plt.show()

# Evaluasi Konsistensi Sentimen dari Prediksi 9 Emosi
pred_sent = [EMOTION_TO_SENTIMENT[EMOTION_9_CLASSES[p]] for p in ep2]
true_sent = [EMOTION_TO_SENTIMENT[EMOTION_9_CLASSES[t]] for t in et2]
sent_implied_acc = accuracy_score(true_sent, pred_sent)
print(f"Konsistensi Sentimen Implisit dari 9 Emosi: {sent_implied_acc*100:.2f}%")

with open(os.path.join(EMO_DIR, 'evaluation_metrics.json'), 'w') as fj:
    json.dump({
        'model': MODEL_NAME, 'task': 'emotion_9class', 'accuracy': float(eacc),
        'macro_precision': float(eprec), 'macro_recall': float(erec), 'macro_f1': float(ef1),
        'implicit_sentiment_accuracy': float(sent_implied_acc),
        'confusion_matrix': cm_emo.tolist(), 'labels': EMOTION_9_CLASSES,
        'emotion_to_sentiment': EMOTION_TO_SENTIMENT
    }, fj, indent=2)


# =====================================================================
# CELL 7: FULL CORPUS INFERENCE (Langkah 4 & 6)
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 4 & 6: INFERENSI 197K CORPUS DENGAN GPU T4")
print("=" * 70)

if os.path.exists(ENRICHED_PATH):
    master = pd.read_parquet(ENRICHED_PATH)
else:
    master = pd.read_csv(MASTER_PATH, low_memory=False)
print(f"Total Korpus yang akan di-inferensi: {len(master):,} baris")

if not os.path.exists(SENT_DIR):
    alt_sent = os.path.join(DRIVE_DIR, 'best_indobert_sentiment')
    if os.path.exists(alt_sent):
        SENT_DIR = alt_sent

s_model = AutoModelForSequenceClassification.from_pretrained(SENT_DIR).to(device)
s_model.eval()
s_tok = AutoTokenizer.from_pretrained(SENT_DIR)

if not os.path.exists(EMO_DIR):
    alt_emo = os.path.join(DRIVE_DIR, 'best_indobert_emotion')
    if os.path.exists(alt_emo):
        EMO_DIR = alt_emo

e_model = AutoModelForSequenceClassification.from_pretrained(EMO_DIR).to(device)
e_model.eval()
e_tok = AutoTokenizer.from_pretrained(EMO_DIR)

def batch_pred(model, tok, texts, bs=128, ml=128):
    preds, probs = [], []
    for i in range(0, len(texts), bs):
        bt = [str(t)[:400] for t in texts[i:i+bs]]
        enc = tok(bt, truncation=True, padding=True, max_length=ml, return_tensors='pt').to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            pb = torch.softmax(logits, 1).cpu().numpy()
        preds.extend(np.argmax(pb, 1))
        probs.append(pb)
        if (i // bs + 1) % 100 == 0 or (i + bs) >= len(texts):
            print(f"  Inferensi: {min(i+bs, len(texts)):,}/{len(texts):,} ({min(i+bs, len(texts))/len(texts)*100:.0f}%)")
    return np.array(preds), np.vstack(probs)

print("\nMemulai Inferensi Sentimen IndoBERT V2...")
sp, sprob = batch_pred(s_model, s_tok, master['cleaned_content'].values, bs=128)
master['sentiment_label'] = sp
master['predicted_sentiment'] = pd.Series(sp).map({0: 'Negatif', 1: 'Netral', 2: 'Positif'}).values
master['sentiment_score'] = sprob[:, 2] - sprob[:, 0]
master['sentiment_name'] = master['predicted_sentiment']

print("\nMemulai Inferensi IndoBERT 9 Emosi...")
epred, eprob = batch_pred(e_model, e_tok, master['cleaned_content'].values, bs=128)
id2label = {int(k): v for k, v in e_model.config.id2label.items()} if hasattr(e_model.config, 'id2label') and e_model.config.id2label else {i: l for i, l in enumerate(EMOTION_9_CLASSES)}
master['emotion'] = pd.Series(epred).map(id2label).values
master['emotion_confidence'] = np.max(eprob, axis=1)
master['emotion_sentiment'] = master['emotion'].map(EMOTION_TO_SENTIMENT)

# Format kolom tanggal & engagement untuk Streamlit & SNA
if 'date' not in master.columns or master['date'].isna().all():
    master['date'] = pd.to_datetime(master['created_at'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')[0], errors='coerce')
master['date_str'] = pd.to_datetime(master['date']).dt.strftime('%Y-%m-%d')
master['year_month'] = pd.to_datetime(master['date']).dt.to_period('M').astype(str)

for c in ['likes', 'comments', 'shares', 'reposts', 'views']:
    if c in master.columns:
        master[c] = pd.to_numeric(master[c], errors='coerce').fillna(0).clip(0, 500000).astype(int)
    else:
        master[c] = 0

master['total_engagement'] = master['likes'] + master['comments'] + master['shares'] + master['reposts']
master['reach'] = master['views'] + (master['likes']*3) + (master['comments']*5) + (master['shares']*10) + (master['reposts']*10)

OUT_CSV = os.path.join(DRIVE_DIR, 'enriched_corpus_for_sna.csv')
OUT_PQ = os.path.join(DRIVE_DIR, 'enriched_corpus_for_sna.parquet')
print("\nMenyimpan hasil inferensi ke Google Drive...")
master.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
master.to_parquet(OUT_PQ, index=False)

print(f"\nDistribusi Sentimen IndoBERT:\n{master['predicted_sentiment'].value_counts().to_string()}")
print(f"\nDistribusi 9 Emosi IndoBERT:\n{master['emotion'].value_counts().to_string()}")
print(f"\nStatistik Sentimen Score:\n{master['sentiment_score'].describe().to_string()}")

# =====================================================================
# CELL 8: BUILD SOCIAL NETWORK ANALYSIS (SNA) BY SENTIMENT & EMOTION
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 7: MEMBANGUN GRAF SNA BY SENTIMENT & EMOTION (INDOBERT)")
print("=" * 70)

import networkx as nx
from collections import defaultdict, Counter

SNA_OUT_DIR = os.path.join(DRIVE_DIR, 'sna_output')
os.makedirs(SNA_OUT_DIR, exist_ok=True)

mention_pattern = re.compile(r'@([A-Za-z0-9_\.]+)')

def build_and_export_sna(df_corpus, topic_name='All_Topics', min_edge_weight=1):
    print(f"\n--- Memproses Graf SNA Topik: {topic_name} ---")
    if topic_name != 'All_Topics':
        df_sub = df_corpus[df_corpus['topic'].astype(str).str.lower() == topic_name.lower()].copy()
    else:
        df_sub = df_corpus.copy()
        
    print(f"Total baris data diproses: {len(df_sub):,} entri")
    
    G = nx.DiGraph()
    author_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    author_emotions = defaultdict(lambda: defaultdict(int))
    author_platforms = {}
    author_engagements = defaultdict(int)
    
    target_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    target_emotions = defaultdict(lambda: defaultdict(int))
    
    edges_dict = defaultdict(lambda: {'weight': 0, 'sentiments': [], 'emotions': []})
    
    for _, row in df_sub.iterrows():
        author = str(row.get('author', row.get('user_id', ''))).strip().lower()
        if not author or author in ['nan', 'none', 'anonim', '']:
            continue
            
        sent = str(row.get('predicted_sentiment', 'Netral'))
        emo = str(row.get('emotion', 'Neutral'))
        plat = str(row.get('platform', 'SocialMedia'))
        eng = int(row.get('total_engagement', 0))
        
        author_sentiments[author][sent] += 1
        author_emotions[author][emo] += 1
        author_platforms[author] = plat
        author_engagements[author] += eng
        
        text = str(row.get('cleaned_content', ''))
        mentions = mention_pattern.findall(text)
        for m in mentions:
            target = m.strip().lower()
            if target and target != author:
                target_sentiments[target][sent] += 1
                target_emotions[target][emo] += 1
                edge_key = (author, target)
                edges_dict[edge_key]['weight'] += 1
                edges_dict[edge_key]['sentiments'].append(sent)
                edges_dict[edge_key]['emotions'].append(emo)
                
    # Tambahkan nodes dengan atribut sentimen & emosi
    all_users = set(author_sentiments.keys()).union(set(target_sentiments.keys()))
    print(f"Total simpul aktor (nodes): {len(all_users):,} entitas")
    
    for u in all_users:
        # Tentukan dominant sentiment (dari postingan sendiri atau dari mention publik)
        s_counts = author_sentiments[u] if sum(author_sentiments[u].values()) > 0 else target_sentiments[u]
        dom_sent = max(s_counts, key=s_counts.get) if s_counts else 'Netral'
        
        # Tentukan dominant emotion (dari 9 emosi)
        e_counts = author_emotions[u] if sum(author_emotions[u].values()) > 0 else target_emotions[u]
        dom_emo = max(e_counts, key=e_counts.get) if e_counts else 'Neutral'
        
        # Net Sentiment Score (NSS) aktor (-100 s/d +100)
        pos_cnt = s_counts.get('Positif', 0)
        neg_cnt = s_counts.get('Negatif', 0)
        tot_cnt = sum(s_counts.values())
        actor_nss = round(((pos_cnt - neg_cnt) / tot_cnt * 100), 2) if tot_cnt > 0 else 0.0
        
        G.add_node(
            u,
            sentiment=dom_sent,
            emotion=dom_emo,
            nss=actor_nss,
            platform=author_platforms.get(u, 'Mentioned'),
            total_engagement=author_engagements.get(u, 0)
        )
        
    # Tambahkan edges berbobot dengan sentimen & emosi relasi
    for (src, tgt), edata in edges_dict.items():
        if edata['weight'] >= min_edge_weight:
            most_sent = Counter(edata['sentiments']).most_common(1)[0][0]
            most_emo = Counter(edata['emotions']).most_common(1)[0][0]
            G.add_edge(src, tgt, weight=edata['weight'], sentiment=most_sent, emotion=most_emo)
            
    print(f"Graf SNA Berhasil Dibangun: {G.number_of_nodes():,} Nodes, {G.number_of_edges():,} Edges")
    
    # Hitung sentralitas jaringan
    in_deg = dict(G.in_degree(weight='weight'))
    out_deg = dict(G.out_degree(weight='weight'))
    nx.set_node_attributes(G, in_deg, 'in_degree')
    nx.set_node_attributes(G, out_deg, 'out_degree')
    
    # Top 15 Influencers by In-Degree (KOL)
    top_inf = sorted(in_deg.items(), key=lambda x: x[1], reverse=True)[:20]
    print(f"\n🌟 Top 10 Influencers by In-Degree Centrality ({topic_name}):")
    print(f"{'No':<3} {'Akun/Tokoh':<25} {'In-Deg':>8} {'Sentimen':>12} {'Emosi':>12} {'NSS':>8}")
    print("-" * 72)
    top_summary = []
    for rank, (u, deg) in enumerate(top_inf, 1):
        nd = G.nodes[u]
        if rank <= 10:
            print(f"{rank:<3} @{u:<24} {deg:>8} {nd['sentiment']:>12} {nd['emotion']:>12} {nd['nss']:>7.1f}%")
        top_summary.append({
            'rank': rank, 'user': u, 'in_degree': deg,
            'out_degree': out_deg.get(u, 0), 'sentiment': nd['sentiment'],
            'emotion': nd['emotion'], 'nss': nd['nss'],
            'platform': nd['platform'], 'engagement': nd['total_engagement']
        })
        
    # Ekspor ke Google Drive untuk Gephi & Dashboard
    prefix = topic_name.lower()
    gexf_file = os.path.join(SNA_OUT_DIR, f"{prefix}_sna_by_sentiment.gexf")
    json_file = os.path.join(SNA_OUT_DIR, f"{prefix}_sna_summary.json")
    
    nx.write_gexf(G, gexf_file)
    with open(json_file, 'w', encoding='utf-8') as fj:
        json.dump({
            'topic': topic_name, 'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(), 'top_influencers': top_summary
        }, fj, indent=2)
        
    print(f"✅ File Gephi (.gexf) siap pakai: {gexf_file}")
    print(f"✅ File Ringkasan JSON: {json_file}")
    return G

# Ekspor SNA untuk All Topics dan Per Topic
g_all = build_and_export_sna(master, 'All_Topics')
for top in ['MBG', 'KDMP', 'Sekolah_Rakyat']:
    if (master['topic'].astype(str).str.lower() == top.lower()).sum() > 0:
        build_and_export_sna(master, top)

print(f"\n{'='*70}")
print(f"🎉 PIPELINE LENGKAP INDOBERT & SNA SELESAI DITRAIN & DI-EXPORT KE GOOGLE DRIVE!")
print(f"{'='*70}")
print(f"File Output Utama di Google Drive ({DRIVE_DIR}):")
print(f"  1. {OUT_PQ}  <-- Dataset korpus bersih dengan Sentimen & 9 Emosi")
print(f"  2. {OUT_CSV}")
print(f"  3. {SENT_DIR}  <-- Folder Checkpoint IndoBERT Sentimen (3-Class)")
print(f"  4. {EMO_DIR}   <-- Folder Checkpoint IndoBERT Emosi (9-Class)")
print(f"  5. {SNA_OUT_DIR}  <-- Graf Gephi (.gexf) & JSON SNA by Sentiment & Emotion")

# =====================================================================
# CELL 9: BACKUP SEMUA HASIL KE ZIP & DOWNLOAD
# =====================================================================
print("\n" + "=" * 70)
print("LANGKAH 8: BACKUP SEMUA HASIL KE FORMAT ZIP & DOWNLOAD")
print("=" * 70)

# pyrefly: ignore [missing-import]
import shutil, os
# pyrefly: ignore [missing-import]
from google.colab import files

TEMP_ZIP = '/content/hasil_training_indobert_sna'

print("📦 Sedang mengompres seluruh hasil training, model, dan SNA ke format ZIP...")
shutil.make_archive(TEMP_ZIP, 'zip', DRIVE_DIR)

drive_zip = os.path.join(DRIVE_DIR, 'hasil_training_indobert_sna.zip')
shutil.copy(f"{TEMP_ZIP}.zip", drive_zip)
print(f"✅ File ZIP permanen berhasil disimpan di Drive: {drive_zip}")

# Munculkan popup download langsung ke browser/laptop
print("⬇️ Memulai download otomatis ke laptop Anda...")
try:
    files.download(drive_zip)
except Exception as e:
    print(f"ℹ️ Info download browser: {e}. Anda tetap bisa mengunduh file zip langsung dari Google Drive di {drive_zip}")


