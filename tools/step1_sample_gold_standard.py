"""
Langkah 1: Stratified Sampling 1.000 Sampel untuk Gold Standard Annotation
Sampling merata dari semua platform, topik, dan sentiment (termasuk kasus sulit)
"""
import pandas as pd
import numpy as np
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PARQUET_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')
OUTPUT_PATH = os.path.join(DATA_DIR, 'gold_standard_sample_1000.csv')

print("=" * 70)
print("📊 STRATIFIED SAMPLING 1.000 SAMPEL UNTUK GOLD STANDARD")
print("=" * 70)

df = pd.read_parquet(PARQUET_PATH)
print(f"Total corpus: {len(df):,} rows")

# ============================================================
# Strategy: 3 tiers of sampling
# ============================================================
# Tier 1 (600 samples): Stratified by platform x topic x sentiment
# Tier 2 (200 samples): "Hard cases" — sarcasm, negation, mixed
# Tier 3 (200 samples): Random from underrepresented platforms
# ============================================================

np.random.seed(42)
selected_indices = set()

# ── Tier 1: Stratified balanced sampling (600) ──
print("\n─── Tier 1: Stratified Sampling (600 sampel) ───")
tier1_target = 600
platforms = df['platform'].unique()
topics = df['topic'].unique()
sentiments = df['sentiment_name'].unique()

# Calculate per-group target
n_groups = len(platforms) * len(topics) * len(sentiments)
per_group = max(2, tier1_target // n_groups)

tier1_indices = []
for platform in platforms:
    for topic in topics:
        for sentiment in sentiments:
            mask = (df['platform'] == platform) & (df['topic'] == topic) & (df['sentiment_name'] == sentiment)
            group = df[mask]
            if len(group) > 0:
                n_take = min(len(group), per_group)
                sampled = group.sample(n_take, random_state=42)
                tier1_indices.extend(sampled.index.tolist())

# If over 600, subsample; if under, that's fine
if len(tier1_indices) > tier1_target:
    tier1_indices = list(np.random.choice(tier1_indices, tier1_target, replace=False))

selected_indices.update(tier1_indices)
print(f"  Tier 1 selected: {len(tier1_indices)} samples")

# ── Tier 2: Hard cases (200) — sarcasm, negation, mixed sentiment ──
print("\n─── Tier 2: Hard Cases (200 sampel) ───")
hard_patterns = [
    # Sarcasm / irony
    'terima kasih.*gagal', 'bagus.*korupsi', 'hebat.*keracunan',
    'mantap.*rusak', 'keren.*bangkrut', 'berhasil.*masalah',
    # Negation
    'tidak bagus', 'tidak berhasil', 'tidak gagal', 'bukan masalah',
    'belum berhasil', 'gak bagus', 'gak keren',
    # Mixed sentiment indicators
    'tapi', 'namun', 'sayangnya', 'padahal', 'seharusnya', 'walaupun',
    # Controversial content
    'keracunan', 'cacing', 'basi', 'korupsi.*berhasil', 'gagal.*sukses',
]

tier2_indices = []
remaining = df.drop(index=list(selected_indices), errors='ignore')

for pattern in hard_patterns:
    matches = remaining[remaining['cleaned_content'].str.lower().str.contains(pattern, na=False, regex=True)]
    if len(matches) > 0:
        n_take = min(len(matches), 15)
        sampled = matches.sample(n_take, random_state=42)
        for idx in sampled.index:
            if idx not in selected_indices and len(tier2_indices) < 200:
                tier2_indices.append(idx)

# Fill remaining with random hard cases (short text, emoji-heavy)
if len(tier2_indices) < 200:
    remaining2 = remaining.drop(index=tier2_indices, errors='ignore')
    # Short texts are harder to classify
    short_texts = remaining2[remaining2['cleaned_content'].str.len().between(10, 50)]
    n_fill = min(200 - len(tier2_indices), len(short_texts))
    if n_fill > 0:
        fill = short_texts.sample(n_fill, random_state=42)
        tier2_indices.extend(fill.index.tolist())

selected_indices.update(tier2_indices)
print(f"  Tier 2 selected: {len(tier2_indices)} samples")

# ── Tier 3: Underrepresented platforms (200) ──
print("\n─── Tier 3: Platform Balance (200 sampel) ───")
tier3_target = 1000 - len(selected_indices)
remaining3 = df.drop(index=list(selected_indices), errors='ignore')

# Prioritize underrepresented: Facebook, YouTube, Instagram, News
underrep_platforms = ['Facebook', 'YouTube', 'Instagram', 'News', 'TikTok', 'Twitter']
tier3_indices = []

per_platform = tier3_target // len(underrep_platforms)
for plat in underrep_platforms:
    plat_data = remaining3[remaining3['platform'] == plat]
    if len(plat_data) > 0:
        n_take = min(len(plat_data), per_platform)
        sampled = plat_data.sample(n_take, random_state=42)
        tier3_indices.extend(sampled.index.tolist())

# Fill any remaining with random
if len(tier3_indices) < tier3_target:
    already = selected_indices | set(tier3_indices)
    remaining4 = df.drop(index=list(already), errors='ignore')
    n_fill = tier3_target - len(tier3_indices)
    if n_fill > 0 and len(remaining4) > 0:
        fill = remaining4.sample(min(n_fill, len(remaining4)), random_state=42)
        tier3_indices.extend(fill.index.tolist())

selected_indices.update(tier3_indices)
print(f"  Tier 3 selected: {len(tier3_indices)} samples")

# ── Compile final sample ──
all_indices = list(selected_indices)[:1000]
sample_df = df.loc[all_indices].copy()
sample_df = sample_df.sample(frac=1.0, random_state=42).reset_index(drop=True)

print(f"\n{'=' * 70}")
print(f"📦 TOTAL SAMPEL TERPILIH: {len(sample_df):,}")
print(f"{'=' * 70}")

print(f"\nDistribusi Platform:")
print(sample_df['platform'].value_counts().to_string())
print(f"\nDistribusi Topik:")
print(sample_df['topic'].value_counts().to_string())
print(f"\nDistribusi Sentimen (rule-based lama):")
print(sample_df['sentiment_name'].value_counts().to_string())

# Save with only essential columns for annotation
cols_to_save = ['platform', 'topic', 'cleaned_content', 'raw_content', 'sentiment_name', 'emotion', 'author', 'url']
sample_df[cols_to_save].to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
print(f"\n💾 Saved to: {OUTPUT_PATH}")
