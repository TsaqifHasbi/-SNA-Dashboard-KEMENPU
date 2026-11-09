"""
Training Data Labeling & Stratified Split for IndoBERT
Mempersiapkan dataset latih 3 kelas: Negatif (0), Netral (1), Positif (2)
"""

import os
import sys
import re
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

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MASTER_PATH = os.path.join(OUTPUT_DIR, 'master_scraped_corpus.csv')

# Kamus Leksikon Sentimen Khusus Kebijakan Publik Indonesia (Domain Adapted)
POSITIVE_LEXICON = set([
    'bagus', 'hebat', 'mantap', 'keren', 'berhasil', 'sukses', 'bermanfaat', 'membantu',
    'apresiasi', 'dukung', 'terima kasih', 'alhamdulillah', 'bersyukur', 'berkah',
    'berkualitas', 'sehat', 'nutrisi', 'bergizi', 'berguna', 'senang', 'bangga',
    'terjamin', 'berkembang', 'maju', 'tumbuh', 'harapan', 'terbukti', 'layak',
    'adil', 'merata', 'beres', 'tuntas', 'untung', 'positif', 'puas', 'juara',
    'menyejahterakan', 'terobosan', 'efisien', 'transparan', 'semangat', 'berdaya'
])

NEGATIVE_LEXICON = set([
    'buruk', 'gagal', 'rusak', 'ambrol', 'hancur', 'kecewa', 'rugi', 'korupsi',
    'bancakan', 'curang', 'bohong', 'palsu', 'maling', 'keracunan', 'beracun', 'basi',
    'bau', 'jorok', 'mual', 'muntah', 'parah', 'krisis', 'marah', 'sesat', 'bobrok',
    'bodoh', 'sengsara', 'beban', 'masalah', 'cacat', 'sunat', 'pencitraan', 'rugikan',
    'penipuan', 'manipulasi', 'terbelakang', 'terpuruk', 'menolak', 'kritik', 'dungu',
    'salah', 'amburadul', 'kecewa', 'merusak', 'ugal-ugalan', 'korban', 'ancaman'
])

# Frasa negasi yang membalik polaritas
NEGATION_WORDS = set(['tidak', 'tak', 'bukan', 'jangan', 'belum', 'gak', 'ga', 'nggak', 'tdk'])

def rule_based_sentiment_scorer(text):
    """
    Menghitung skor sentimen berbasis leksikon kontekstual & polaritas negasi.
    Return:
        0: Negatif
        1: Netral
        2: Positif
    """
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 1
    
    pos_score = 0
    neg_score = 0
    
    for i, w in enumerate(words):
        # Cek apakah didahului kata negasi (window 1-2 kata sebelumnya)
        is_negated = False
        if i > 0 and words[i-1] in NEGATION_WORDS:
            is_negated = True
        elif i > 1 and words[i-2] in NEGATION_WORDS:
            is_negated = True
            
        if w in POSITIVE_LEXICON:
            if is_negated:
                neg_score += 1.5 # Contoh: "tidak bagus" -> negatif
            else:
                pos_score += 1.0
        elif w in NEGATIVE_LEXICON:
            if is_negated:
                pos_score += 1.0 # Contoh: "tidak rusak" -> positif/netral
            else:
                neg_score += 1.5
                
    # Evaluasi polaritas
    diff = pos_score - neg_score
    if diff >= 1.0:
        return 2  # Positif
    elif diff <= -1.0:
        return 0  # Negatif
    else:
        return 1  # Netral (Deskriptif, laporan berita objektif, statistik)

def prepare_labeled_dataset(sample_size=30000):
    """
    Menyiapkan dataset berlabel untuk fine-tuning IndoBERT.
    Mengambil sampel representatif seimbang antar topik dan platform.
    """
    print("\n" + "=" * 75)
    print("🏷️  MEMPERSIAPKAN DATASET ANOTASI DENGAN STRATIFIKASI UNTUK INDOBERT")
    print("=" * 75)
    
    if not os.path.exists(MASTER_PATH):
        print(f"[!] File master belum ada. Menjalankan konsolidasi terlebih dahulu...")
        from dataset_preparation import consolidate_all_platforms
        df = consolidate_all_platforms()
    else:
        df = pd.read_csv(MASTER_PATH, low_memory=False)
        
    print(f"Total Master Corpus: {len(df):,} baris")
    
    # Beri label otomatis berbasis leksikon kontekstual terkalibrasi
    print("Menjalankan pelabelan berbasis leksikon kontekstual...")
    df['label'] = df['cleaned_content'].apply(rule_based_sentiment_scorer)
    
    label_map = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}
    df['sentiment'] = df['label'].map(label_map)
    
    print("\nDistribusi Sentimen pada Seluruh Corpus:")
    print(df['sentiment'].value_counts())
    
    # Ambil sampel berimbang untuk dataset training IndoBERT (misal 30.000 data representatif)
    target_per_group = int(sample_size / (len(df['topic'].unique()) * 3))
    sample_indices = []
    for (t, l), group in df.groupby(['topic', 'label']):
        n_take = min(len(group), target_per_group)
        sample_indices.extend(group.sample(n_take, random_state=42).index.tolist())
        
    sample_df = df.loc[sample_indices].sample(frac=1.0, random_state=42).copy().reset_index(drop=True)
    
    print(f"\nUkuran Dataset Training IndoBERT Terpilih: {len(sample_df):,} baris")
    print("Distribusi Kelas Dataset Training:")
    print(sample_df['sentiment'].value_counts())
    
    # Split Train (80%), Val (10%), Test (10%)
    train_df, temp_df = train_test_split(
        sample_df, test_size=0.20, random_state=42, stratify=sample_df['label']
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=42, stratify=temp_df['label']
    )
    
    print(f"\n📦 Pembagian Dataset:")
    print(f"   - Train Set (80%)      : {len(train_df):,} baris")
    print(f"   - Validation Set (10%) : {len(val_df):,} baris")
    print(f"   - Test Set (10%)       : {len(test_df):,} baris")
    
    # Simpan ke folder data/
    train_df.to_csv(os.path.join(OUTPUT_DIR, 'train.csv'), index=False, encoding='utf-8-sig')
    val_df.to_csv(os.path.join(OUTPUT_DIR, 'val.csv'), index=False, encoding='utf-8-sig')
    test_df.to_csv(os.path.join(OUTPUT_DIR, 'test.csv'), index=False, encoding='utf-8-sig')
    
    print(f"\n💾 Berhasil menyimpan train.csv, val.csv, dan test.csv ke {OUTPUT_DIR}")
    return train_df, val_df, test_df

if __name__ == '__main__':
    prepare_labeled_dataset()
