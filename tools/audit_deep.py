import pandas as pd, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
PARQUET_PATH = os.path.join(PROJECT_ROOT, 'data', 'enriched_corpus_for_sna.parquet')
df = pd.read_parquet(PARQUET_PATH)

# Deep adversarial: show actual texts classified wrong
print('='*80)
print('EXAMPLES: Text with "keracunan" but classified POSITIF')
print('='*80)
sus = df[(df['sentiment_name']=='Positif') & (df['cleaned_content'].str.lower().str.contains('keracunan', na=False))].head(5)
for _, r in sus.iterrows():
    plat = r['platform']
    text = str(r['cleaned_content'])[:250]
    print(f'  [{plat}] {text}')
    print()

print('='*80)
print('EXAMPLES: Text with "berhasil" but classified NEGATIF')
print('='*80)
sus2 = df[(df['sentiment_name']=='Negatif') & (df['cleaned_content'].str.lower().str.contains('berhasil', na=False))].head(5)
for _, r in sus2.iterrows():
    plat = r['platform']
    text = str(r['cleaned_content'])[:250]
    print(f'  [{plat}] {text}')
    print()

print('='*80)
print('EXAMPLES: Text with "cacing" labeled POSITIF')
print('='*80)
sus3 = df[(df['sentiment_name']=='Positif') & (df['cleaned_content'].str.lower().str.contains('cacing', na=False))]
print(f'Total: {len(sus3)}')
for _, r in sus3.head(3).iterrows():
    plat = r['platform']
    text = str(r['cleaned_content'])[:250]
    print(f'  [{plat}] {text}')
    print()

# Check training data: was it labeled with actual model or rule-based?
print('='*80)
print('KEY QUESTION: Was inferensi done with IndoBERT or rule-based fallback?')
print('='*80)
unique_scores = df['sentiment_score'].unique()
print(f'Unique scores: {sorted(unique_scores)}')
if len(unique_scores) <= 3:
    print('>>> ONLY 3 DISCRETE SCORES (-0.75, 0.0, 0.75)')
    print('>>> This means the RULE-BASED fallback was used, NOT the IndoBERT model!')
    print('>>> The infer_sentiment.py code assigns these exact values when model is unavailable.')
else:
    print(f'>>> {len(unique_scores)} unique scores - IndoBERT continuous probabilities were used.')
