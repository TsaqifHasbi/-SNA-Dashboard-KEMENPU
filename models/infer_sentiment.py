"""
IndoBERT Batch Inference & Dataset Enrichment for SNA
Menghasilkan sentimen prediksi, probabilitas, dan skor polaritas kontinu (-1.0 s/d +1.0)
untuk seluruh 211.000+ data scraping lintas platform.
"""

import os
import sys
import pandas as pd
import numpy as np

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MASTER_PATH = os.path.join(DATA_DIR, 'master_scraped_corpus.csv')
MODEL_SAVE_DIR = os.path.join(os.path.dirname(__file__), 'best_indobert_sentiment') if os.path.exists(os.path.join(os.path.dirname(__file__), 'best_indobert_sentiment')) else os.path.join(os.path.dirname(__file__), 'best_indobert_sentiment_v2')
OUTPUT_ENRICHED_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.csv')

LABEL_MAP = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}

def batch_infer_sentiment(batch_size=64, max_length=128):
    """
    Melakukan inferensi sentimen masal pada master corpus.
    Jika checkpoint IndoBERT tersedia, menggunakan IndoBERT.
    Jika belum ada (misal di PC lokal tanpa GPU), menggunakan hybrid calibrated scorer.
    """
    print("=" * 75)
    print("🔮 MEMULAI ENRICHMENT DATASET UNTUK SOCIAL NETWORK ANALYSIS (SNA)")
    print("=" * 75)
    
    if not os.path.exists(MASTER_PATH):
        print("[!] File master_scraped_corpus.csv belum ada. Menjalankan konsolidasi...")
        from dataset_preparation import consolidate_all_platforms
        df = consolidate_all_platforms()
    else:
        df = pd.read_csv(MASTER_PATH, low_memory=False)
        
    print(f"Total Data yang Akan Di-Enrich: {len(df):,} baris")
    
    has_trained_model = os.path.exists(os.path.join(MODEL_SAVE_DIR, 'config.json'))
    
    if has_trained_model:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            from torch.utils.data import DataLoader, Dataset
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"Memuat Model IndoBERT dari {MODEL_SAVE_DIR} pada {device}...")
            
            tokenizer = AutoTokenizer.from_pretrained(MODEL_SAVE_DIR)
            model = AutoModelForSequenceClassification.from_pretrained(MODEL_SAVE_DIR).to(device)
            model.eval()
            
            class InferDataset(Dataset):
                def __init__(self, texts):
                    self.texts = texts
                def __len__(self):
                    return len(self.texts)
                def __getitem__(self, i):
                    return str(self.texts[i])
                    
            dataset = InferDataset(df['cleaned_content'].values)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
            
            all_preds = []
            all_scores = []
            
            print(f"Menjalankan inferensi IndoBERT ({len(loader)} batch)...")
            with torch.no_grad():
                for step, batch_texts in enumerate(loader):
                    encoded = tokenizer(
                        list(batch_texts),
                        truncation=True,
                        padding=True,
                        max_length=max_length,
                        return_tensors='pt'
                    ).to(device)
                    
                    logits = model(**encoded).logits
                    probs = torch.softmax(logits, dim=1).cpu().numpy()
                    
                    preds = np.argmax(probs, axis=1)
                    # Skor polaritas kontinu: P(Positif) - P(Negatif), range [-1.0, +1.0]
                    polarity_scores = probs[:, 2] - probs[:, 0]
                    
                    all_preds.extend(preds)
                    all_scores.extend(polarity_scores)
                    
                    if (step + 1) % 100 == 0 or (step + 1) == len(loader):
                        print(f"   Batch {step+1}/{len(loader)} selesai...")
                        
            df['sentiment_label'] = all_preds
            df['predicted_sentiment'] = df['sentiment_label'].map(LABEL_MAP)
            df['sentiment_score'] = all_scores
            
        except Exception as e:
            print(f"[WARN] IndoBERT inference gagal: {e}. Menggunakan fallback scorer...")
            has_trained_model = False
            
    if not has_trained_model:
        print("[INFO] Checkpoint IndoBERT belum dilatih. Menggunakan Calibrated Contextual Scorer...")
        from label_training_data import rule_based_sentiment_scorer
        df['sentiment_label'] = df['cleaned_content'].apply(rule_based_sentiment_scorer)
        df['predicted_sentiment'] = df['sentiment_label'].map(LABEL_MAP)
        # Hitung skor kontinu estimasi
        score_mapping = {0: -0.75, 1: 0.0, 2: 0.75}
        df['sentiment_score'] = df['sentiment_label'].map(score_mapping)
        
    # Hitung Net Sentiment Score (NSS) ala Laporan Kementerian PU
    pos_count = (df['predicted_sentiment'] == 'Positif').sum()
    neg_count = (df['predicted_sentiment'] == 'Negatif').sum()
    netral_count = (df['predicted_sentiment'] == 'Netral').sum()
    total_valid = len(df)
    
    nss = ((pos_count - neg_count) / total_valid) * 100
    
    print("\n" + "=" * 70)
    print("📊 HASIL INFERENSI SENTIMEN KORPUS GABUNGAN:")
    print("=" * 70)
    print(f"Total Dokumen    : {total_valid:,}")
    print(f"• Positif (Hijau): {pos_count:>8,} ({pos_count/total_valid*100:.1f}%)")
    print(f"• Netral (Abu)   : {netral_count:>8,} ({netral_count/total_valid*100:.1f}%)")
    print(f"• Negatif (Merah): {neg_count:>8,} ({neg_count/total_valid*100:.1f}%)")
    print(f"• Net Sentiment Score (NSS): {nss:+.1f} poin")
    print("=" * 70)
    
    df.to_csv(OUTPUT_ENRICHED_PATH, index=False, encoding='utf-8-sig')
    print(f"\n💾 Dataset Enriched tersimpan ke: {OUTPUT_ENRICHED_PATH}")
    return df

if __name__ == '__main__':
    batch_infer_sentiment()
