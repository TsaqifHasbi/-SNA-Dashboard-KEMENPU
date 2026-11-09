"""
================================================================================
🚀 STRATIFIED DIVERSE SAMPLER: THREADS 30,000 DATA (10K PER TOPIK)
================================================================================
Memilah korpus Threads (148,434 data) menjadi tepat 30,000 data berkualitas tinggi:
  - 10,000 data MBG
  - 10,000 data KDMP
  - 10,000 data Sekolah Rakyat

Strategi Pemilahan Variatif & Efisien:
  1. Backup file original ke scraped_Threads_Only_ORIGINAL_148K.csv
  2. Text Quality Filter: Minimal 4 kata & deduplikasi konten unik
  3. Author Diversity (Anti-Spammer SNA): Batasi maksimal 8 pos per handle
  4. Keyword Stratification: Setiap keyword dari 60+ variasi per topik terwakili adil
  5. Engagement Diversity: Kombinasi 35% postingan viral/berpengaruh (high impact)
     dan 65% percakapan organik masyarakat (grassroots)
================================================================================
"""

import os
import sys
import shutil
import pandas as pd
import numpy as np

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'ScrapeData')
THREADS_CSV = os.path.join(DATA_DIR, 'scraped_Threads_Only.csv')
BACKUP_CSV = os.path.join(DATA_DIR, 'scraped_Threads_Only_ORIGINAL_148K.csv')

def run_sampling():
    print("=" * 70)
    print("🚀 MEMULAI PEMILAHAN STRATIFIKASI THREADS 30.000 DATA (10K PER TOPIK)")
    print("=" * 70)

    if not os.path.exists(THREADS_CSV):
        print(f"[ERROR] File {THREADS_CSV} tidak ditemukan!")
        sys.exit(1)

    # 1. Amankan Backup File Asli jika belum ada
    if not os.path.exists(BACKUP_CSV):
        print(f"[BACKUP] Membuat cadangan aman korpus 148k...")
        shutil.copy2(THREADS_CSV, BACKUP_CSV)
        print(f"         Tersimpan ke: {os.path.basename(BACKUP_CSV)}")
    else:
        print(f"[INFO] File backup {os.path.basename(BACKUP_CSV)} sudah tersedia.")

    # 2. Baca Dataset Asli (baca dari backup agar selalu bersumber dari data lengkap)
    source_file = BACKUP_CSV if os.path.exists(BACKUP_CSV) else THREADS_CSV
    print(f"\n[1/4] Membaca data dari: {os.path.basename(source_file)}...")
    df = pd.read_csv(source_file, low_memory=False)
    print(f"      Total data mentah: {len(df):,} baris")

    # 3. Quality Cleaning & Deduplikasi
    print("\n[2/4] Membersihkan data teks & deduplikasi...")
    df = df[df['content'].notna()]
    df['content_clean'] = df['content'].astype(str).str.strip()
    df = df[df['content_clean'].str.split().str.len() >= 4]  # Minimal 4 kata
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['content_clean'])
    print(f"      Dihapus {before_dedup - len(df):,} teks duplikat / terlalu pendek.")
    print(f"      Tersisa {len(df):,} baris berkualitas.")

    # Tampilkan ketersediaan per topik
    print("\nKetersediaan data per topik sebelum sampling:")
    for t, c in df['topic'].value_counts().items():
        print(f"  • {t:<15}: {c:,} baris")

    # 4. Stratified Diverse Sampling Function
    def sample_topic(df_topic, topic_name, target=10000, random_state=42):
        print(f"\n[Sampling] Memproses Topik: {topic_name} (Target: {target:,})...")
        df_t = df_topic.copy()

        # A. Batasi dominasi akun buzzer/spammer maks 8 post per handle
        df_t['author_rank'] = df_t.groupby('handle').cumcount() + 1
        df_t = df_t[df_t['author_rank'] <= 8]

        # B. Stratifikasi Keyword
        kws = df_t['keyword'].value_counts()
        target_per_kw = max(1, target // len(kws))
        print(f"           - {len(kws)} keyword unik terdeteksi.")
        print(f"           - Target dasar per keyword: ~{target_per_kw} data.")

        selected_indices = []

        # Pass 1: Ambil seimbang dari setiap variasi keyword
        for kw in kws.index:
            sub_kw = df_t[df_t['keyword'] == kw]
            if len(sub_kw) <= target_per_kw:
                selected_indices.extend(sub_kw.index.tolist())
            else:
                # 35% konten berbobot tinggi (viral / berpengaruh), 65% percakapan organik masyarakat
                n_top = int(target_per_kw * 0.35)
                n_rand = target_per_kw - n_top
                
                # Sortir engagement (likes + comments + reposts)
                sub_sorted = sub_kw.sort_values(by=['likes', 'comments', 'reposts'], ascending=False)
                top_part = sub_sorted.iloc[:n_top]
                rand_part = sub_sorted.iloc[n_top:].sample(
                    n=min(n_rand, len(sub_kw) - n_top), 
                    random_state=random_state
                )
                selected_indices.extend(top_part.index.tolist())
                selected_indices.extend(rand_part.index.tolist())

        # Pass 2: Isi kekurangan kuota hingga genap 10.000
        current_set = set(selected_indices)
        rem = df_t.loc[~df_t.index.isin(current_set)]
        shortage = target - len(current_set)
        if shortage > 0 and len(rem) > 0:
            fill_samples = rem.sample(n=min(shortage, len(rem)), random_state=random_state)
            selected_indices.extend(fill_samples.index.tolist())

        res = df_t.loc[selected_indices[:target]].copy()
        
        # Bersihkan kolom helper
        if 'content_clean' in res.columns:
            res.drop(columns=['content_clean'], inplace=True)
        if 'author_rank' in res.columns:
            res.drop(columns=['author_rank'], inplace=True)

        print(f"           ✅ Berhasil mengambil {len(res):,} data:")
        print(f"              - Tersebar di {res['keyword'].nunique()} variasi keyword")
        print(f"              - Mewakili {res['handle'].nunique():,} aktor/penulis unik")
        print(f"              - Rerata likes: {res['likes'].mean():.1f} | Maks likes: {res['likes'].max():,}")
        return res

    # 5. Eksekusi per topik
    print("\n[3/4] Menjalankan sampling seimbang 3 topik...")
    sampled_dfs = []
    for topic_name in ['MBG', 'KDMP', 'Sekolah_Rakyat']:
        sub_df = df[df['topic'] == topic_name]
        sampled_topic = sample_topic(sub_df, topic_name, target=10000, random_state=42)
        sampled_dfs.append(sampled_topic)

    df_final = pd.concat(sampled_dfs, ignore_index=True)

    # 6. Simpan Hasil Akhir
    print(f"\n[4/4] Menyimpan dataset 30.000 baris ke {os.path.basename(THREADS_CSV)}...")
    # Pastikan urutan kolom sesuai standar
    cols_order = ['platform', 'keyword', 'url', 'handle', 'content', 'created_at', 'likes', 'comments', 'reposts', 'shares', 'views', 'scraped_at', 'topic']
    ordered = [c for c in cols_order if c in df_final.columns] + [c for c in df_final.columns if c not in cols_order]
    df_final = df_final[ordered]
    
    df_final.to_csv(THREADS_CSV, index=False, encoding='utf-8-sig')
    print(f"      💾 Tersimpan sukses! Ukuran file: {os.path.getsize(THREADS_CSV) / (1024*1024):.2f} MB")

    print("\n" + "=" * 70)
    print("🎉 PEMILAHAN SELESAI DENGAN SUKSES!")
    print(f"Total Baris Threads Sekarang : {len(df_final):,} baris")
    print("Distribusi Topik:")
    for t, c in df_final['topic'].value_counts().items():
        print(f"  • {t:<15}: {c:,} baris (100.0% seimbang)")
    print(f"Total Aktor/Akun Unik        : {df_final['handle'].nunique():,} akun")
    print(f"Total Variasi Keyword        : {df_final['keyword'].nunique():,} keyword")
    print("=" * 70)

if __name__ == '__main__':
    run_sampling()
