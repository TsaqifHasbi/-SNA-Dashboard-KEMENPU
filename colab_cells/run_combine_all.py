import os
import sys
import re
import html
import unicodedata
import pandas as pd
from cell_02_config import OUTPUT_DIR

# Import aturan regex relevansi topik & noise dari modul resmi project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.execute_all_platforms_filter import (
    pat_kemenpu_core, pat_kemenpu_cooccur,
    pat_menpu_core, pat_menpu_cooccur,
    pat_fatal_noise, pat_context_noise
)

print("="*60)
print("🚀 MENGGABUNGKAN & MEMBERSIHKAN SEMUA HASIL SCRAPING KEMEN PU")
print("="*60)

def clean_social_text(text):
    """
    Pembersihan teks NLP multiplatform:
    1. Decode HTML entities (&amp; -> &, &quot; -> ", dll)
    2. Hapus tautan URL di dalam kalimat teks
    3. Hapus karakter line-terminator aneh (\u2028, \u2029, \r, dll)
    4. Reduksi pemanjangan huruf berulang (asuuuu -> asu, kerennn -> keren)
    5. Normalisasi spasi berlebih
    """
    if not text or not isinstance(text, str):
        return ''
    t = html.unescape(text)
    t = re.sub(r'https?://\S+|www\.\S+', '', t)
    t = re.sub(r'[\u2028\u2029\r\x0b\x0c\x85]', ' ', t)
    t = re.sub(r'(.)\1{2,}', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# Cari semua file CSV yang namanya dimulai dari "scraped_" dan berakhiran "_Only.csv"
all_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("scraped_") and f.endswith("_Only.csv")]

if not all_files:
    print("Tidak ditemukan file CSV hasil scraping di folder ScrapeData.")
    sys.exit(0)

dataframes = []
for file in all_files:
    path = os.path.join(OUTPUT_DIR, file)
    print(f"Membaca {file}...")
    try:
        df = pd.read_csv(path, low_memory=False)
        dataframes.append(df)
    except Exception as e:
        print(f"Gagal membaca {file}: {e}")

if not dataframes:
    print("Semua file CSV kosong.")
    sys.exit(0)

# 1. Gabungkan Semua Platform
combined_df = pd.concat(dataframes, ignore_index=True)
awal = len(combined_df)
print(f"\nTotal Data Keseluruhan (Mentah): {awal:,} baris")

dropped_records = []

# 2. Hapus Duplikat URL
if 'url' in combined_df.columns:
    dup_url_mask = combined_df.duplicated(subset=['url'], keep='first')
    if dup_url_mask.any():
        dropped_url = combined_df[dup_url_mask].copy()
        dropped_url['alasan_dibuang'] = 'Duplikat URL (Sudah ada di baris lain)'
        dropped_records.extend(dropped_url.to_dict(orient='records'))

    combined_df = combined_df[~dup_url_mask].copy()
    akhir_url = len(combined_df)
    print(f"Dihapus {awal - akhir_url:,} duplikat URL. Sisa: {akhir_url:,} baris")

# 3. Standarisasi Kolom Aktor & Identitas
if 'author' not in combined_df.columns and 'handle' in combined_df.columns:
    combined_df['author'] = combined_df['handle']
elif 'author' in combined_df.columns and 'handle' in combined_df.columns:
    combined_df['author'] = combined_df['author'].fillna(combined_df['handle']).fillna('anonim')
elif 'author' not in combined_df.columns:
    combined_df['author'] = 'anonim'

if 'user_id' not in combined_df.columns:
    combined_df['user_id'] = combined_df['author']

# 4. Hapus Baris Kosong & Simpan raw_content
if 'content' not in combined_df.columns and 'description' in combined_df.columns:
    combined_df['content'] = combined_df['description']

empty_mask = combined_df['content'].isna() | (combined_df['content'].astype(str).str.strip().str.len() < 5)
if empty_mask.any():
    dropped_empty = combined_df[empty_mask].copy()
    dropped_empty['alasan_dibuang'] = 'Teks Kosong atau Kurang dari 5 Karakter'
    dropped_records.extend(dropped_empty.to_dict(orient='records'))

combined_df = combined_df[~empty_mask].copy()
combined_df['raw_content'] = combined_df['content'].astype(str)

# 5. Filter Relevansi Topik & Eliminasi Noise (Two-Tiered Architecture)
print("\n[PROSES] Memeriksa relevansi topik (Kementerian_PU / Menteri_PU) & menyaring noise...")

def normalize_text_for_eval(text):
    t = html.unescape(str(text))
    t = unicodedata.normalize('NFKD', t)
    t = re.sub(r'[\u00a0\u200b\u200c\u200d\u202f\ufeff]', ' ', t)
    return t

eval_text = combined_df['raw_content'].apply(normalize_text_for_eval)

match_menpu = eval_text.str.contains(pat_menpu_core) | eval_text.str.contains(pat_menpu_cooccur)
match_kemenpu = eval_text.str.contains(pat_kemenpu_core) | eval_text.str.contains(pat_kemenpu_cooccur)

has_any_topic = match_menpu | match_kemenpu
has_strong_core = eval_text.str.contains(pat_menpu_core) | eval_text.str.contains(pat_kemenpu_core)

hits_fatal = eval_text.str.contains(pat_fatal_noise)
hits_context = eval_text.str.contains(pat_context_noise)
hits_noise = hits_fatal | (hits_context & (~has_strong_core))

keep_topic_mask = has_any_topic & (~hits_noise)
discard_topic_mask = ~keep_topic_mask

if discard_topic_mask.any():
    dropped_topic = combined_df[discard_topic_mask].copy()
    reasons = []
    for idx in dropped_topic.index:
        if hits_fatal.loc[idx]:
            reasons.append('Spam Fatal / Entitas Asing (Judi/Slot/Crypto/Gaming/Vespa)')
        elif hits_context.loc[idx] and not has_strong_core.loc[idx]:
            reasons.append('Noise Kontekstual Tanpa Entitas PU Inti')
        else:
            reasons.append('Konten Nyasar (Tidak Memuat Kata Kunci Kementerian PU / Menteri PU)')
    dropped_topic['alasan_dibuang'] = reasons
    dropped_records.extend(dropped_topic.to_dict(orient='records'))

before_topic_filter = len(combined_df)
combined_df = combined_df[keep_topic_mask].copy()
print(f"Dihapus {before_topic_filter - len(combined_df):,} konten nyasar / noise non-topik. Sisa: {len(combined_df):,} baris")

# Rekonsiliasi Topik (Menteri_PU vs Kementerian_PU)
combined_df['topic'] = 'Kementerian_PU'
is_menpu_final = eval_text.loc[combined_df.index].str.contains(pat_menpu_core)
combined_df.loc[is_menpu_final, 'topic'] = 'Menteri_PU'

# 6. Pembersihan Teks Mendalam (NLP Preprocessing) -> Menghasilkan cleaned_content
print("\n[PROSES] Membersihkan teks NLP (Decode HTML, hapus link, reduksi huruf berulang)...")
combined_df['cleaned_content'] = combined_df['raw_content'].apply(clean_social_text)

too_short_mask = combined_df['cleaned_content'].str.len() < 4
if too_short_mask.any():
    dropped_short = combined_df[too_short_mask].copy()
    dropped_short['alasan_dibuang'] = 'Teks Kosong/Hanya Simbol/Link Setelah Dibersihkan'
    dropped_records.extend(dropped_short.to_dict(orient='records'))

combined_df = combined_df[~too_short_mask].copy()

# 7. Deduplikasi Lanjutan: Postingan persis sama oleh akun yang sama
dup_author_content = combined_df.duplicated(subset=['author', 'cleaned_content'], keep='first')
if dup_author_content.any():
    dropped_dup = combined_df[dup_author_content].copy()
    dropped_dup['alasan_dibuang'] = 'Duplikat Teks dari Keyword Lain'
    dropped_records.extend(dropped_dup.to_dict(orient='records'))

before_author_dup = len(combined_df)
combined_df = combined_df[~dup_author_content].copy()
print(f"Dihapus {before_author_dup - len(combined_df):,} salinan duplikat per author. Sisa: {len(combined_df):,} baris")

# Sinkronkan kolom content dengan cleaned_content
combined_df['content'] = combined_df['cleaned_content']

# 8. Hitung Total Engagement
for col in ['likes', 'comments', 'shares', 'reposts', 'views']:
    if col in combined_df.columns:
        combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0).astype(int)
    else:
        combined_df[col] = 0

combined_df['total_engagement'] = (
    combined_df['likes'] + combined_df['comments'] + 
    combined_df['shares'] + combined_df['reposts'] + combined_df['views']
)

# 9. Simpan ke File Akhir
final_path = os.path.join(OUTPUT_DIR, "FINAL_ALL_DATA.csv")
colab_path = os.path.join(OUTPUT_DIR, "scraped_ALL_combined.csv")
dropped_path = os.path.join(OUTPUT_DIR, "DATA_YANG_DIBUANG_CLEANING.csv")

data_dir = os.path.join(BASE_DIR, 'data')
os.makedirs(data_dir, exist_ok=True)
master_corpus_path = os.path.join(data_dir, "master_scraped_corpus.csv")

combined_df.to_csv(final_path, index=False, encoding='utf-8-sig')
combined_df.to_csv(colab_path, index=False, encoding='utf-8-sig')

# Simpan juga format master_scraped_corpus.csv untuk pipeline training & inference
target_cols = ['platform', 'topic', 'keyword', 'user_id', 'author', 'handle', 'url', 'raw_content', 'cleaned_content', 'created_at', 'likes', 'comments', 'shares', 'reposts', 'views', 'total_engagement']
available_cols = [c for c in target_cols if c in combined_df.columns]
df_master = combined_df[available_cols].copy()
df_master.to_csv(master_corpus_path, index=False, encoding='utf-8-sig')

df_dropped = pd.DataFrame(dropped_records)
df_dropped.to_csv(dropped_path, index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print(f"🎉 SUKSES! Data Kemen PU berhasil digabung dan dibersihkan secara NLP.")
print(f"Total Data Bersih  : {len(combined_df):,} Baris")
print(f"Total Data Dibuang : {len(df_dropped):,} Baris")
print(f"Tersimpan di:")
print(f"   1. Data Bersih (Master): {final_path}")
print(f"   2. Data Bersih (Colab) : {colab_path}")
print(f"   3. Master Corpus (ML)  : {master_corpus_path}")
print(f"   4. Data yang Dibuang   : {dropped_path}")
print("="*60)
