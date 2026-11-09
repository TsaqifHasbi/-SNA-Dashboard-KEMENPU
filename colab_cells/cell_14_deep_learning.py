# ============================================================
# CELL 14: DEEP LEARNING PIPELINE (SENTIMEN & EMOSI)
# Menggunakan pre-trained model IndoBERT / IndoRoBERTa
# Pastikan Runtime Colab menggunakan T4 GPU agar cepat!
# ============================================================
import pandas as pd
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
from transformers import pipeline
from tqdm.auto import tqdm
import os
import time

# Memaksa tqdm berjalan di environment Colab dengan baik
tqdm.pandas()

print("=" * 60)
print("[PROSES] MEMULAI PIPELINE DEEP LEARNING (SENTIMENT & EMOTION)")
print("=" * 60)

# Cek apakah GPU tersedia
device = 0 if torch.cuda.is_available() else -1
if device == 0:
    print(f"[INFO] Hardware Acceleration: GPU Ditemukan ({torch.cuda.get_device_name(0)}) 🚀")
else:
    print("[WARNING] GPU TIDAK DITEMUKAN! Proses akan memakan waktu SANGAT LAMA di CPU.")
    print("         -> Pergi ke menu 'Runtime' > 'Change runtime type' > Pilih 'T4 GPU'.")

# ============================================================
# 1. LOAD DATA BERSIH
# ============================================================
input_path = '/content/drive/MyDrive/ScrapeData/scraped_ALL_combined.csv'
output_path = '/content/drive/MyDrive/ScrapeData/scraped_ALL_analyzed.csv'

if not os.path.exists(input_path):
    raise FileNotFoundError(f"[!] File {input_path} tidak ditemukan. Pastikan Cell 12 berhasil dijalankan.")

print(f"\n[INFO] Membaca data dari: {input_path}")
df = pd.read_csv(input_path)
print(f"[OK] {len(df)} baris data siap diproses.")

# Pastikan kolom content tidak ada yang kosong atau tipe data salah
df['content'] = df['content'].fillna('').astype(str)

# ============================================================
# 2. INISIALISASI MODEL HUGGINGFACE
# ============================================================
print("\n[INFO] Mengunduh & memuat model Deep Learning (sekitar 1-2 GB)...")
start_time = time.time()

# Model Sentimen (Positif, Netral, Negatif)
try:
    sentiment_model_name = "w11wo/indonesian-roberta-base-sentiment-classifier"
    sentiment_pipeline = pipeline("text-classification", model=sentiment_model_name, device=device, truncation=True, max_length=512)
    print("   [OK] Model Sentiment berhasil dimuat.")
except Exception as e:
    print(f"   [!] Gagal memuat model Sentiment: {e}")
    sentiment_pipeline = None

# Model Emosi (Anger, Happy, Sad, Fear, Love, Surprise)
try:
    emotion_model_name = "StevenLimcorn/indonesian-roberta-base-emotion-classifier"
    emotion_pipeline = pipeline("text-classification", model=emotion_model_name, device=device, truncation=True, max_length=512)
    print("   [OK] Model Emotion berhasil dimuat.")
except Exception as e:
    print(f"   [!] Gagal memuat model Emotion: {e}")
    emotion_pipeline = None

print(f"[INFO] Waktu memuat model: {time.time() - start_time:.2f} detik")

# ============================================================
# 3. FUNGSI PREDIKSI BATCH (Untuk kecepatan optimal)
# ============================================================
def batch_inference(data_list, model_pipeline, batch_size=64):
    if not model_pipeline:
        return ["error"] * len(data_list)
        
    results = []
    # Menggunakan pipeline generator untuk efisiensi RAM dan GPU
    for out in tqdm(model_pipeline(data_list, batch_size=batch_size), total=len(data_list), desc="  Predicting"):
        # out bentuknya: {'label': 'positive', 'score': 0.98}
        results.append(out['label'])
    return results

# Ekstraksi hanya 512 karakter pertama agar tidak error Out Of Memory
texts_to_predict = df['content'].str[:512].tolist()

# ============================================================
# 4. EKSEKUSI SENTIMENT ANALYSIS
# ============================================================
print(f"\n[PROSES] 1/2: Menjalankan Analisis Sentimen untuk {len(df)} baris...")
if sentiment_pipeline:
    start_time = time.time()
    sentiments = batch_inference(texts_to_predict, sentiment_pipeline, batch_size=128)
    # Mapping output label (tergantung model) menjadi format baku
    df['sentiment'] = [str(s).capitalize() for s in sentiments]
    print(f"[OK] Analisis Sentimen selesai dalam {time.time() - start_time:.2f} detik.")
else:
    df['sentiment'] = "Unknown"

# ============================================================
# 5. EKSEKUSI EMOTION ANALYSIS
# ============================================================
print(f"\n[PROSES] 2/2: Menjalankan Analisis Emosi untuk {len(df)} baris...")
if emotion_pipeline:
    start_time = time.time()
    emotions = batch_inference(texts_to_predict, emotion_pipeline, batch_size=128)
    df['emotion'] = [str(e).capitalize() for e in emotions]
    print(f"[OK] Analisis Emosi selesai dalam {time.time() - start_time:.2f} detik.")
else:
    df['emotion'] = "Unknown"

# ============================================================
# 6. SIMPAN & PREVIEW HASIL
# ============================================================
print("\n[INFO] Menyimpan hasil Deep Learning...")
df.to_csv(output_path, index=False)
df.to_json(output_path.replace('.csv', '.json'), orient='records', lines=True)
print(f"[OK] Data berhasil disimpan di: {output_path}")

print("\n" + "="*60)
print("[STATISTIK HASIL DEEP LEARNING]")
print("="*60)

if 'sentiment' in df.columns:
    print("\n--- Distribusi Sentimen ---")
    print(df['sentiment'].value_counts())

if 'emotion' in df.columns:
    print("\n--- Distribusi Emosi ---")
    print(df['emotion'].value_counts())

print("\n[PREVIEW DATA TERBARU]")
display_cols = ['platform', 'topic', 'content', 'sentiment', 'emotion']
print(df[display_cols].head(10))

print("\n[SELESAI] Data siap digunakan untuk Dashboard Streamlit! 🎉")
