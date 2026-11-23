"""
================================================================================
🎯 RUNNER PIPELINE BERTAHAP KEMEN PU: 5 NOVEMBER 2026 s.d. HARI INI DETIK INI
Kementerian Pekerjaan Umum Republik Indonesia (Kemen PU)
================================================================================
Arsitektur Bertahap (Decoupled Pipeline):
  - TAHAP 1 (SCRAPING MURNI):
    Tarik semua data dari keyword yang ada (5 Nov s.d. Hari Ini Detik Ini) di 7
    platform tanpa membuang data yang melenceng saat scraping.
  - TAHAP 2 (CLEANING & FILTERING TOPIK):
    Bereskan data yang melenceng, buang Dinas PU Pemda murni, pertahankan Balai &
    Balai Besar vertikal KemenPU, serta pertahankan Buzzer (URL berbeda).
    Hasilkan FINAL_ALL_DATA.csv & DATA_YANG_DIBUANG_CLEANING.csv. (BERHENTI).
  - TAHAP 3 (LABELING SENTIMEN, EMOSI & WILAYAH):
    Jalankan IndoBERT + Sentiment Corrector + 9 Emosi Plutchik + Deteksi Daerah
    Terdampak pada data yang sudah bersih. (BERHENTI).
  - TAHAP 4 (SINKRONISASI POSTGRESQL):
    Push/migrasi hasil akhir ke database PostgreSQL.

Cara Menjalankan (Key Run Bertahap):
  [TAHAP 1 - SCRAPING MURNI]
  python run_scrape_nov05_20.py news         -> Scrape Berita Online (Google & Bing)
  python run_scrape_nov05_20.py youtube      -> Scrape YouTube
  python run_scrape_nov05_20.py twitter      -> Scrape Twitter / X
  python run_scrape_nov05_20.py instagram    -> Scrape Instagram
  python run_scrape_nov05_20.py tiktok       -> Scrape TikTok
  python run_scrape_nov05_20.py threads      -> Scrape Threads
  python run_scrape_nov05_20.py facebook     -> Scrape Facebook
  python run_scrape_nov05_20.py all          -> Scrape SEMUA 7 Platform Murni (Tanpa Cleaning/Labeling)

  [TAHAP 2 - CLEANING DATA SAJA]
  python run_scrape_nov05_20.py clean        -> Gabung & Cleaning Topik (Tanpa Labeling)

  [TAHAP 3 - LABELING SENTIMEN, EMOSI & DAERAH SAJA]
  python run_scrape_nov05_20.py label        -> Labeling IndoBERT + Emosi + Daerah

  [TAHAP 4 - PUSH KE DATABASE POSTGRESQL]
  python run_scrape_nov05_20.py db           -> Migrasi Parquet ke PostgreSQL

  [CEK STATUS DATA]
  python run_scrape_nov05_20.py status       -> Lihat tabel ringkasan data per platform
================================================================================
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
import pandas as pd

# Fix encoding console Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CELLS_DIR = os.path.join(BASE_DIR, 'colab_cells')
SCRAPE_DIR = os.path.join(BASE_DIR, 'ScrapeData')
TOOLS_DIR = os.path.join(BASE_DIR, 'tools')

# Rentang Tanggal Default: 5 November 2026 s.d. Hari Ini Detik Ini (Real-Time)
DEFAULT_SINCE = "2026-11-05"
DEFAULT_UNTIL = datetime.now().strftime("%Y-%m-%d")
NOW_FULL_STR = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")

PLATFORM_MAP = {
    'news':      ('scraped_News_Only.csv',      'run_news_only.py',      'Berita Online (Google/Bing)'),
    'youtube':   ('scraped_YouTube_Only.csv',   'run_youtube_only.py',   'YouTube'),
    'twitter':   ('scraped_Twitter_Only.csv',   'run_twitter_only.py',   'Twitter / X'),
    'instagram': ('scraped_Instagram_Only.csv', 'run_instagram_only.py', 'Instagram'),
    'tiktok':    ('scraped_TikTok_Only.csv',    'run_tiktok_only.py',    'TikTok'),
    'threads':   ('scraped_Threads_Only.csv',   'run_threads_only.py',   'Threads'),
    'facebook':  ('scraped_Facebook_Only.csv',  'run_facebook_only.py',  'Facebook')
}

# Alias pendek agar lebih praktis
ALIASES = {
    'berita': 'news',
    'yt': 'youtube',
    'x': 'twitter',
    'ig': 'instagram',
    'tt': 'tiktok',
    'th': 'threads',
    'fb': 'facebook',
    'scrape_all': 'all',
    'cleaning': 'clean',
    'combine': 'clean',
    'labeling': 'label',
    'postgres': 'db',
}

def count_platform_stats(csv_file, since_str, until_str):
    """Menghitung total baris dan baris dalam rentang tanggal target."""
    csv_path = os.path.join(SCRAPE_DIR, csv_file)
    if not os.path.exists(csv_path):
        return 0, 0
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        total = len(df)
        if 'created_at' in df.columns:
            s = df['created_at'].astype(str).str.replace(' WIB', '').str.strip()
            dt = pd.to_datetime(s, errors='coerce')
            sub = df[(dt >= since_str) & (dt <= f"{until_str} 23:59:59")]
            in_range = len(sub)
        else:
            in_range = 0
        return total, in_range
    except Exception:
        return 0, 0

def print_banner(stage_title, since_str, until_str):
    now_exact = datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
    print("=" * 78)
    print(f"🎯 {stage_title}")
    print("=" * 78)
    print(f"📅 Rentang Tanggal    : {since_str} 00:00:00 s.d. {until_str} (Real-time: {now_exact})")
    print(f"🔑 Sumber Keyword     : TOPICS Resmi cell_02_config.py (Kementerian_PU & Menteri_PU)")
    print(f"📁 Direktori Simpan   : {SCRAPE_DIR}")
    print(f"🛡️ Mode Scraping      : RAW CAPTURE (Data melenceng disimpan dulu, dibersihkan di Tahap 2)")
    print("=" * 78)

def run_single_platform(platform_key, since_str=DEFAULT_SINCE, until_str=DEFAULT_UNTIL, start_kw=None):
    """TAHAP 1: Menjalankan scraping murni pada 1 platform tanpa cleaning/labeling."""
    platform_key = ALIASES.get(platform_key.lower(), platform_key.lower())
    
    if platform_key not in PLATFORM_MAP:
        print(f"❌ Platform '{platform_key}' tidak dikenali.")
        print(f"   Pilihan: {', '.join(PLATFORM_MAP.keys())}, all, clean, label, db, status")
        return False

    csv_file, script_name, display_name = PLATFORM_MAP[platform_key]
    script_path = os.path.join(CELLS_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"❌ Script runner tidak ditemukan: {script_path}")
        return False

    total_before, in_range_before = count_platform_stats(csv_file, since_str, until_str)
    print(f"\n📊 [STATUS SEBELUM] {display_name} ({csv_file}):")
    print(f"   - Total data tersimpan     : {total_before:,} baris")
    print(f"   - Data periode target      : {in_range_before:,} baris ({since_str} s.d. {until_str})")

    # Hitung until+1 hari untuk query eksklusif (Twitter/Google 'until:' / 'before:' sifatnya eksklusif)
    try:
        dt_until = datetime.strptime(until_str, '%Y-%m-%d')
        until_plus_1 = (dt_until + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        until_plus_1 = until_str

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["SCRAPE_SINCE"] = since_str
    env["SCRAPE_UNTIL"] = until_plus_1
    env["SCRAPE_TARGETED"] = "1"
    env["SCRAPE_RAW_MODE"] = "1"
    if start_kw:
        env["START_KW"] = str(start_kw)
        print(f"⏩ [JUMP] Memulai scraping dari keyword #{start_kw} ke atas")

    print(f"\n▶ [TAHAP 1: SCRAPING MURNI] Menjalankan {display_name}...")
    cmd = [sys.executable, "-u", script_name]

    try:
        ret = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        total_after, in_range_after = count_platform_stats(csv_file, since_str, until_str)
        added = max(0, total_after - total_before)
        added_in_range = max(0, in_range_after - in_range_before)

        print("\n" + "-" * 72)
        print(f"✅ [SELESAI SCRAPING] {display_name}:")
        print(f"   - Data baru ditambahkan                 : +{added:,} baris")
        print(f"   - Tambahan di rentang ({since_str} - sekarang): +{added_in_range:,} baris")
        print(f"   - Total akhir di {csv_file:<22} : {total_after:,} baris ({in_range_after:,} periode target)")
        print("-" * 72)
        return ret.returncode == 0
    except KeyboardInterrupt:
        print(f"\n⚠️ Proses scraping {display_name} dihentikan pengguna.")
        return False

def run_stage_cleaning():
    """TAHAP 2: Hanya menggabungkan CSV mentah & menyaring topik yang melenceng (TANPA LABELING)."""
    print("\n" + "=" * 78)
    print("🧹 [TAHAP 2: CLEANING & FILTERING TOPIK SAJA — TANPA LABELING]")
    print("=" * 78)
    print("   - Menggabungkan seluruh file scraped_*_Only.csv dari 7 platform")
    print("   - Memisahkan data yang melenceng / noise ke DATA_YANG_DIBUANG_CLEANING.csv")
    print("   - Membuang Dinas PU Pemda murni & mempertahankan Balai/Balai Besar UPT KemenPU")
    print("   - Mempertahankan Buzzer (teks sama persis dengan URL berbeda tetap disimpan)")
    print("=" * 78)

    combine_script = os.path.join(CELLS_DIR, 'run_combine_all.py')
    if os.path.exists(combine_script):
        cmd = [sys.executable, "-u", 'run_combine_all.py']
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        res = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        if res.returncode != 0:
            print("❌ Gagal saat menjalankan Tahap 2 (Cleaning).")
            return False
        print("\n" + "=" * 78)
        print("✅ TAHAP 2 (CLEANING DATA) SELESAI!")
        print("   - Data Bersih  : ScrapeData/FINAL_ALL_DATA.csv & data/master_scraped_corpus.csv")
        print("   - Data Dibuang : ScrapeData/DATA_YANG_DIBUANG_CLEANING.csv")
        print("👉 Silakan cek hasil cleaning terlebih dahulu.")
        print("👉 Jika sudah siap lanjut ke TAHAP 3 (Labeling Sentimen & Emosi), jalankan:")
        print("   python run_scrape_nov05_20.py label")
        print("=" * 78)
        return True
    else:
        print(f"❌ Script cleaning tidak ditemukan di {combine_script}")
        return False

def run_stage_labeling():
    """TAHAP 3: Hanya menjalankan Labeling Sentimen, Emosi, Daerah Terdampak & Isu pada data bersih."""
    print("\n" + "=" * 78)
    print("🏷️  [TAHAP 3: LABELING SENTIMEN, EMOSI & DETEKSI WILAYAH]")
    print("=" * 78)
    print("   - Membaca data hasil cleaning: data/master_scraped_corpus.csv")
    print("   - Menjalankan IndoBERT + Korektor Sentimen (Anti-Sarkas, Perpus, Netralisasi ESDM)")
    print("   - Menyelaraskan 9-Emosi Plutchik & mengekstraksi Wilayah Terdampak + Klaster Isu")
    print("=" * 78)

    sync_script = os.path.join(TOOLS_DIR, 'sync_and_enrich_corpus.py')
    if os.path.exists(sync_script):
        cmd = [sys.executable, "-u", sync_script]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        res = subprocess.run(cmd, cwd=BASE_DIR, env=env)
        if res.returncode != 0:
            print("❌ Gagal saat menjalankan Tahap 3 (Labeling).")
            return False
        print("\n" + "=" * 78)
        print("✅ TAHAP 3 (LABELING SENTIMEN, EMOSI & WILAYAH) SELESAI!")
        print("   - Tersimpan di : data/enriched_corpus_for_sna.parquet & data/enriched_corpus_for_sna.csv")
        print("👉 Jika ingin menyinkronkan ke database PostgreSQL (TAHAP 4), jalankan:")
        print("   python run_scrape_nov05_20.py db")
        print("=" * 78)
        return True
    else:
        print(f"❌ Script labeling tidak ditemukan di {sync_script}")
        return False

def run_stage_db():
    """TAHAP 4: Migrasi Parquet berlabel ke PostgreSQL."""
    print("\n" + "=" * 78)
    print("🗄️  [TAHAP 4: SINKRONISASI KE DATABASE POSTGRESQL]")
    print("=" * 78)
    db_script = os.path.join(TOOLS_DIR, 'migrate_parquet_to_postgres.py')
    if os.path.exists(db_script):
        cmd = [sys.executable, "-u", db_script]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        res = subprocess.run(cmd, cwd=BASE_DIR, env=env)
        return res.returncode == 0
    else:
        print(f"❌ Script migrasi DB tidak ditemukan di {db_script}")
        return False

def show_interactive_menu(since_str, until_str):
    print("=" * 78)
    print(f"🎯 MENU PIPELINE BERTAHAP KEMEN PU ({since_str} s.d. {until_str} / Detik Ini)")
    print("=" * 78)
    print("  --- TAHAP 1: SCRAPING MURNI (Tanpa Cleaning / Tanpa Labeling) ---")
    print("  [1] Scrape Berita Online (Google News & Bing)")
    print("  [2] Scrape YouTube (YouTube Data API v3)")
    print("  [3] Scrape Twitter / X (Selenium)")
    print("  [4] Scrape Instagram (Selenium)")
    print("  [5] Scrape TikTok (Selenium)")
    print("  [6] Scrape Threads (API + Selenium)")
    print("  [7] Scrape Facebook (Selenium)")
    print("  [8] Scrape SEMUA 7 Platform Murni (Berhenti setelah CSV mentah terkumpul)")
    print("")
    print("  --- TAHAP 2: CLEANING & FILTERING TOPIK SAJA ---")
    print("  [9] Jalankan Sesi Cleaning Data Saja (Hasilkan FINAL_ALL_DATA & DATA_YANG_DIBUANG)")
    print("")
    print("  --- TAHAP 3: LABELING SENTIMEN, EMOSI & WILAYAH SAJA ---")
    print("  [10] Jalankan Sesi Labeling Sentimen, 9-Emosi & Deteksi Wilayah")
    print("")
    print("  --- TAHAP 4: DATABASE POSTGRESQL ---")
    print("  [11] Migrasi Data Berlabel ke PostgreSQL")
    print("  [0] Keluar")
    print("=" * 78)
    
    choice = input("Pilih nomor tahap [0-11]: ").strip()
    mapping = {
        '1': 'news',
        '2': 'youtube',
        '3': 'twitter',
        '4': 'instagram',
        '5': 'tiktok',
        '6': 'threads',
        '7': 'facebook',
        '8': 'all',
        '9': 'clean',
        '10': 'label',
        '11': 'db'
    }
    return mapping.get(choice)

def print_summary_table(since_str=DEFAULT_SINCE, until_str=DEFAULT_UNTIL):
    """Menampilkan tabel ringkasan data saat ini untuk periode target."""
    print("\n" + "=" * 78)
    print(f"📊 STATUS DATA MENTAH PER PLATFORM ({since_str} s.d. {until_str})")
    print("=" * 78)
    print(f"{'Platform':<28} | {'Total Seluruhnya':<18} | {f'Periode ({since_str}..{until_str})':<24}")
    print("-" * 78)
    tot_all = 0
    tot_rng = 0
    for p_key, (csv_file, _, display_name) in PLATFORM_MAP.items():
        t, r = count_platform_stats(csv_file, since_str, until_str)
        tot_all += t
        tot_rng += r
        print(f"{display_name:<28} | {t:>12,} baris | {r:>18,} baris")
    print("-" * 78)
    print(f"{'TOTAL DATA MENTAH':<28} | {tot_all:>12,} baris | {tot_rng:>18,} baris")
    print("=" * 78 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Runner Pipeline Bertahap Kemen PU (5 Nov 2026 s.d. Hari Ini Detik Ini)",
        usage="python run_scrape_nov05_20.py [action] [--since YYYY-MM-DD] [--until YYYY-MM-DD]"
    )
    parser.add_argument(
        'action',
        nargs='?',
        default=None,
        help="Tahap/Platform: news, youtube, twitter, instagram, tiktok, threads, facebook, all (scrape murni), clean (tahap 2), label (tahap 3), db (tahap 4), status"
    )
    parser.add_argument(
        '--since',
        type=str,
        default=DEFAULT_SINCE,
        help=f"Tanggal mulai (default: {DEFAULT_SINCE})"
    )
    parser.add_argument(
        '--until',
        type=str,
        default=DEFAULT_UNTIL,
        help=f"Tanggal akhir (default: hari ini {DEFAULT_UNTIL})"
    )
    parser.add_argument(
        '--start-kw',
        type=int,
        default=None,
        help="Nomor urut keyword awal untuk memulai"
    )

    args = parser.parse_args()
    target_action = args.action

    if target_action == 'status':
        print_summary_table(args.since, args.until)
        return

    print_summary_table(args.since, args.until)

    if not target_action:
        target_action = show_interactive_menu(args.since, args.until)
        if not target_action:
            print("Keluar.")
            return

    target_action = ALIASES.get(target_action.lower(), target_action.lower())

    # TAHAP 2: CLEANING SAJA
    if target_action == 'clean':
        run_stage_cleaning()
        return

    # TAHAP 3: LABELING SAJA
    if target_action == 'label':
        run_stage_labeling()
        return

    # TAHAP 4: MIGRASI DB POSTGRESQL SAJA
    if target_action == 'db':
        run_stage_db()
        return

    # TAHAP 1: SCRAPING SEMUA PLATFORM MURNI (TANPA CLEANING & TANPA LABELING)
    if target_action == 'all':
        print_banner("TAHAP 1: SCRAPING MURNI SEMUA 7 PLATFORM", args.since, args.until)
        for p in PLATFORM_MAP.keys():
            run_single_platform(p, args.since, args.until, start_kw=args.start_kw)
        print("\n" + "=" * 78)
        print("🎉 TAHAP 1 (SCRAPING MURNI 7 PLATFORM) SELESAI!")
        print("   Seluruh data mentah dari keyword telah disimpan di folder ScrapeData/.")
        print("   Belum dilakukan cleaning/pembuangan topik maupun labeling.")
        print("👉 Untuk melanjutkan ke TAHAP 2 (Cleaning Topik), jalankan perintah:")
        print("   python run_scrape_nov05_20.py clean")
        print("=" * 78)
        return

    # TAHAP 1: SCRAPING SATU PLATFORM MURNI
    if target_action in PLATFORM_MAP:
        print_banner(f"TAHAP 1: SCRAPING MURNI - {PLATFORM_MAP[target_action][2].upper()}", args.since, args.until)
        run_single_platform(target_action, args.since, args.until, start_kw=args.start_kw)
        print(f"\n💡 Data mentah {PLATFORM_MAP[target_action][2]} selesai disimpan.")
        print(f"   Jika seluruh platform yang diinginkan sudah di-scrape, lanjut ke Tahap 2 (Cleaning):")
        print(f"   python run_scrape_nov05_20.py clean")
    else:
        print(f"❌ Pilihan tidak valid: {target_action}")
        print(f"   Pilihan yang tersedia: {', '.join(PLATFORM_MAP.keys())}, all, clean, label, db, status")

if __name__ == '__main__':
    main()
