import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd
from src.sentiment_corrector import correct_sentiment, align_emotion_valence_9class

PARQUET_PATH = 'data/enriched_corpus_for_sna.parquet'
CSV_PATH = 'data/enriched_corpus_for_sna.csv'

print(f"Membaca {PARQUET_PATH}...")
df = pd.read_parquet(PARQUET_PATH)
total = len(df)
print(f"Total baris: {total:,}")

print("\n1. Menerapkan Aturan Koreksi Sentimen (Sarkasme, Negatif Kuat, Positif Kuat)...")
corrected_sents = []
for t, s in zip(df['cleaned_content'], df['predicted_sentiment']):
    cs, _, _, _ = correct_sentiment(t, s, 0.0)
    corrected_sents.append(cs)

df['sentiment_name'] = corrected_sents
df['predicted_sentiment'] = corrected_sents
df['sentiment_label'] = df['sentiment_name'].map({'Negatif': 0, 'Netral': 1, 'Positif': 2}).fillna(1).astype('int8')

print("2. Menerapkan Penyelarasan Valensi Emosi 9-Kelas Plutchik (Anti-Sarkasme Joy)...")
aligned_emos = []
for t, s, e in zip(df['cleaned_content'], df['sentiment_name'], df['emotion']):
    ae = align_emotion_valence_9class(t, s, e)
    aligned_emos.append(ae)

df['emotion'] = aligned_emos

EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral'
}
df['emotion_sentiment'] = df['emotion'].map(EMOTION_TO_SENTIMENT).fillna('Netral')

print("\n3. Menyimpan hasil permanen ke parquet & CSV...")
df.to_parquet(PARQUET_PATH, engine='pyarrow', index=False)
print(f"✅ Berhasil diperbarui: {PARQUET_PATH}")

if os.path.exists(CSV_PATH):
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"✅ Berhasil diperbarui: {CSV_PATH}")

print("\n=== VERIFIKASI AKHIR ===")
print("Distribusi Sentimen Keseluruhan:")
print(df['sentiment_name'].value_counts(normalize=True)*100)

print("\nDistribusi 9 Emosi Keseluruhan:")
print(df['emotion'].value_counts(normalize=True)*100)

print("\nDistribusi Emosi Afektif MBG:")
mbg_aff = df[(df['topic']=='MBG') & (~df['emotion'].str.lower().isin(['neutral', 'netral', 'informatif']))]['emotion']
print((mbg_aff.value_counts(normalize=True)*100).round(1))
