import pandas as pd
import sys, io, random, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
PARQUET_PATH = os.path.join(PROJECT_ROOT, 'data', 'enriched_corpus_for_sna.parquet')
df = pd.read_parquet(PARQUET_PATH)

# =====================================================================
# 1. SPOT CHECK: Manual inspection of sample predictions
# =====================================================================
print('=' * 80)
print('SPOT-CHECK: 5 Random POSITIF Samples')
print('=' * 80)
pos = df[df['sentiment_name'] == 'Positif'].sample(5, random_state=42)
for _, r in pos.iterrows():
    text = str(r['cleaned_content'])[:250]
    sc = r['sentiment_score']
    emo = r['emotion']
    plat = r['platform']
    print(f'[POSITIF | score={sc:.2f} | emotion={emo} | platform={plat}]')
    print(f'  {text}')
    print()

print('=' * 80)
print('SPOT-CHECK: 5 Random NEGATIF Samples')
print('=' * 80)
neg = df[df['sentiment_name'] == 'Negatif'].sample(5, random_state=42)
for _, r in neg.iterrows():
    text = str(r['cleaned_content'])[:250]
    sc = r['sentiment_score']
    emo = r['emotion']
    plat = r['platform']
    print(f'[NEGATIF | score={sc:.2f} | emotion={emo} | platform={plat}]')
    print(f'  {text}')
    print()

print('=' * 80)
print('SPOT-CHECK: 5 Random NETRAL Samples')
print('=' * 80)
neu = df[df['sentiment_name'] == 'Netral'].sample(5, random_state=42)
for _, r in neu.iterrows():
    text = str(r['cleaned_content'])[:250]
    sc = r['sentiment_score']
    emo = r['emotion']
    plat = r['platform']
    print(f'[NETRAL | score={sc:.2f} | emotion={emo} | platform={plat}]')
    print(f'  {text}')
    print()

# =====================================================================
# 2. Check if sentiment_score is continuous or discrete
# =====================================================================
print('=' * 80)
print('SENTIMENT SCORE UNIQUE VALUES (top 20)')
print('=' * 80)
print(df['sentiment_score'].value_counts().head(20).to_string())
print()

# =====================================================================
# 3. Check emotion vs sentiment cross-tab
# =====================================================================
print('=' * 80)
print('EMOTION vs SENTIMENT CROSS-TAB')
print('=' * 80)
ct = pd.crosstab(df['emotion'], df['sentiment_name'], normalize='index')
print((ct * 100).round(1).to_string())
print()

# =====================================================================
# 4. Adversarial check: obviously negative text labeled positive?
# =====================================================================
print('=' * 80)
print('ADVERSARIAL CHECK: Strong negative words in POSITIF predictions')
print('=' * 80)
strong_neg = ['korupsi', 'keracunan', 'gagal', 'kecewa', 'marah', 'borok', 'brengsek']
pos_df = df[df['sentiment_name'] == 'Positif']
for word in strong_neg:
    count = pos_df['cleaned_content'].str.lower().str.contains(word, na=False).sum()
    pct = count / len(pos_df) * 100
    print(f'  "{word}" found in {count:,} POSITIF posts ({pct:.2f}%)')
print()

print('=' * 80)
print('ADVERSARIAL CHECK: Strong positive words in NEGATIF predictions')
print('=' * 80)
strong_pos = ['bagus', 'mantap', 'berhasil', 'sukses', 'hebat', 'keren']
neg_df = df[df['sentiment_name'] == 'Negatif']
for word in strong_pos:
    count = neg_df['cleaned_content'].str.lower().str.contains(word, na=False).sum()
    pct = count / len(neg_df) * 100
    print(f'  "{word}" found in {count:,} NEGATIF posts ({pct:.2f}%)')
print()

# =====================================================================
# 5. Check how many scraped data files exist in ScrapeData folder
# =====================================================================
import os
print('=' * 80)
print('SCRAPED DATA INVENTORY')
print('=' * 80)
scrape_dir = r'..\IndoBERT_SNA_MT_PP\ScrapeData'
for f in sorted(os.listdir(scrape_dir)):
    fp = os.path.join(scrape_dir, f)
    sz = os.path.getsize(fp)
    sdf = pd.read_csv(fp, nrows=2)
    total = len(pd.read_csv(fp))
    print(f'  {f}: {total:,} rows ({sz/1024/1024:.1f} MB)')
print()

# =====================================================================
# 6. Check the master_scraped_corpus vs enriched mismatch
# =====================================================================
print('=' * 80)
print('MASTER vs ENRICHED COMPARISON')
print('=' * 80)
master = pd.read_csv(r'..\IndoBERT_SNA_MT_PP\data\master_scraped_corpus.csv', nrows=5)
print(f'Master columns: {master.columns.tolist()}')
enriched = df
print(f'Enriched columns: {enriched.columns.tolist()}')
print(f'Master rows (estimated): {len(pd.read_csv(r"..\IndoBERT_SNA_MT_PP\data\master_scraped_corpus.csv")):,}')
print(f'Enriched rows: {len(enriched):,}')
