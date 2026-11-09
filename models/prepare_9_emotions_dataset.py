"""
Script Generator Dataset 9 Emosi untuk Fine-Tuning IndoBERT
Tugas Akhir: IndoBERT & SNA Intelligence Dashboard

Struktur 9 Emosi:
- Positif (3): Percaya, Antisipasi, Joy
- Negatif (4): Jijik, Takut, Sedih, Marah
- Netral  (2): Surprise, Informatif

Metode Sampling: Stratified Balanced Sampling (2.500 per kelas = 22.500 baris)
Split: Train 80% (18.000), Val 10% (2.250), Test 10% (2.250)
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'IndoBERT_SNA_MT_PP'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PARQUET_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')

# 9 Target Emotion Classes (English Plutchik standard)
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

LABEL2ID = {name: idx for idx, name in enumerate(EMOTION_9_CLASSES)}
ID2LABEL = {idx: name for idx, name in enumerate(EMOTION_9_CLASSES)}

EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif',
    'Anticipation': 'Positif',
    'Joy': 'Positif',
    'Disgust': 'Negatif',
    'Fear': 'Negatif',
    'Sadness': 'Negatif',
    'Anger': 'Negatif',
    'Surprise': 'Netral',
    'Neutral': 'Netral'
}

def load_and_standardize_corpus():
    print(f"Loading corpus from {PARQUET_PATH}...")
    df = pd.read_parquet(PARQUET_PATH)
    print(f"Total baris dalam korpus: {len(df):,}")

    # Standardize label names to 9 English emotion taxonomy
    mapping = {
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
    df['emotion_9'] = df['emotion'].replace(mapping)
    
    # Filter only rows with valid 9 emotion labels and non-empty text
    df = df[df['emotion_9'].isin(EMOTION_9_CLASSES)].copy()
    df = df.dropna(subset=['cleaned_content'])
    df['cleaned_content'] = df['cleaned_content'].astype(str)
    df = df[df['cleaned_content'].str.strip().str.len() > 10]
    
    print("\nDistribusi 9 Emosi dalam Korpus Keseluruhan:")
    vc = df['emotion_9'].value_counts()
    for emo in EMOTION_9_CLASSES:
        cnt = vc.get(emo, 0)
        sent = EMOTION_TO_SENTIMENT[emo]
        print(f"  [{sent.upper():7s}] {emo:12s}: {cnt:>7,} baris")
        
    return df

def generate_balanced_splits(df, samples_per_class=3500, random_state=42):
    print(f"\nMelakukan Stratified Balanced Sampling ({samples_per_class:,} per kelas) dengan Keseimbangan Antar-Platform...")
    
    sampled_dfs = []
    for emo in EMOTION_9_CLASSES:
        subset = df[df['emotion_9'] == emo]
        n_avail = len(subset)
        n_take_total = min(samples_per_class, n_avail)
        if n_take_total < samples_per_class:
            print(f"  ⚠️ Peringatan: Kelas '{emo}' hanya memiliki {n_avail} sampel (mengambil semua {n_avail}).")
        
        # Cegah dominasi platform tunggal dengan membatasi maksimal ~45% dari satu platform
        max_per_platform = int(n_take_total * 0.45)
        subs = []
        for plat in subset['platform'].unique():
            p_match = subset[subset['platform'] == plat]
            p_take = min(len(p_match), max_per_platform)
            if p_take > 0:
                subs.append(p_match.sample(n=p_take, random_state=random_state))
                
        comb = pd.concat(subs)
        if len(comb) > n_take_total:
            comb = comb.sample(n=n_take_total, random_state=random_state)
        elif len(comb) < n_take_total:
            rem_needed = n_take_total - len(comb)
            rem_pool = subset[~subset.index.isin(comb.index)]
            if len(rem_pool) > 0:
                comb = pd.concat([comb, rem_pool.sample(n=min(rem_needed, len(rem_pool)), random_state=random_state)])
                
        sampled_dfs.append(comb)
        
    balanced_df = pd.concat(sampled_dfs).sample(frac=1, random_state=random_state).reset_index(drop=True)
    balanced_df['label'] = balanced_df['emotion_9'].map(LABEL2ID)
    balanced_df['sentiment'] = balanced_df['emotion_9'].map(EMOTION_TO_SENTIMENT)
    
    print(f"\nTotal dataset seimbang: {len(balanced_df):,} baris")
    print("\nSebaran Platform pada Dataset Seimbang:")
    print(balanced_df['platform'].value_counts().to_string())
    
    # Train (80%) vs Temp (20%)
    train_df, temp_df = train_test_split(
        balanced_df, 
        test_size=0.20, 
        random_state=random_state, 
        stratify=balanced_df['label']
    )
    
    # Val (10%) vs Test (10%)
    val_df, test_df = train_test_split(
        temp_df, 
        test_size=0.50, 
        random_state=random_state, 
        stratify=temp_df['label']
    )
    
    print(f"\nHasil Pembagian Dataset:")
    print(f"  - Train Set : {len(train_df):,} baris ({len(train_df)/len(balanced_df)*100:.0f}%)")
    print(f"  - Val Set   : {len(val_df):,} baris ({len(val_df)/len(balanced_df)*100:.0f}%)")
    print(f"  - Test Set  : {len(test_df):,} baris ({len(test_df)/len(balanced_df)*100:.0f}%)")
    
    # Save CSVs
    train_path = os.path.join(DATA_DIR, 'train_emotion_9.csv')
    val_path = os.path.join(DATA_DIR, 'val_emotion_9.csv')
    test_path = os.path.join(DATA_DIR, 'test_emotion_9.csv')
    
    cols_to_save = ['cleaned_content', 'emotion_9', 'label', 'sentiment', 'platform', 'topic']
    train_df[cols_to_save].to_csv(train_path, index=False, encoding='utf-8')
    val_df[cols_to_save].to_csv(val_path, index=False, encoding='utf-8')
    test_df[cols_to_save].to_csv(test_path, index=False, encoding='utf-8')
    
    print(f"\nFile tersimpan:")
    print(f"  ✅ {train_path}")
    print(f"  ✅ {val_path}")
    print(f"  ✅ {test_path}")

    # Metadata json
    meta_path = os.path.join(DATA_DIR, 'emotion_9_metadata.json')
    meta = {
        'classes': EMOTION_9_CLASSES,
        'label2id': LABEL2ID,
        'id2label': ID2LABEL,
        'emotion_to_sentiment': EMOTION_TO_SENTIMENT,
        'samples_per_class': samples_per_class,
        'total_train': len(train_df),
        'total_val': len(val_df),
        'total_test': len(test_df)
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(meta, f, indent=2)
    print(f"  ✅ {meta_path}")

if __name__ == '__main__':
    df = load_and_standardize_corpus()
    generate_balanced_splits(df, samples_per_class=3500)
