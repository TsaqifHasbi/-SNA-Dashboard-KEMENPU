"""
================================================================================
🎯 RUNNER SCRAPING DATA: 9 s.d. 15 NOVEMBER 2026
Kementerian Pekerjaan Umum Republik Indonesia (Kemen PU)
================================================================================
Runner khusus penarikan data baru rentang 9 s.d. 15 November 2026.
File ini terpisah dan TIDAK MENGUBAH runner/data lama yang sudah ada.

Fitur:
  - Mode Simpan: APPEND & DEDUP (data lama tetap aman, data baru ditambahkan)
  - Key run per platform independen: bisa jalankan satu per satu platform
  - Filter tanggal otomatis: sejak 2026-11-09 hingga 2026-11-15

Cara Menjalankan:
  python run_scrape_nov09_15.py twitter      -> Scrape Twitter / X
  python run_scrape_nov09_15.py news         -> Scrape Berita Online (Google & Bing)
  python run_scrape_nov09_15.py youtube      -> Scrape YouTube
  python run_scrape_nov09_15.py instagram    -> Scrape Instagram
  python run_scrape_nov09_15.py tiktok       -> Scrape TikTok
  python run_scrape_nov09_15.py threads      -> Scrape Threads
  python run_scrape_nov09_15.py facebook     -> Scrape Facebook
  python run_scrape_nov09_15.py combine      -> Gabung semua hasil ke scraped_ALL_combined.csv
  python run_scrape_nov09_15.py all          -> Jalankan semua platform sekaligus berurutan
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

# Rentang Tanggal Default
DEFAULT_SINCE = "2026-11-09"
DEFAULT_UNTIL = "2026-11-18"

PLATFORM_MAP = {
    'twitter':   ('scraped_Twitter_Only.csv',   'run_twitter_only.py',   'Twitter / X'),
    'news':      ('scraped_News_Only.csv',      'run_news_only.py',      'Berita Online (Google/Bing)'),
    'youtube':   ('scraped_YouTube_Only.csv',   'run_youtube_only.py',   'YouTube'),
    'instagram': ('scraped_Instagram_Only.csv', 'run_instagram_only.py', 'Instagram'),
    'tiktok':    ('scraped_TikTok_Only.csv',    'run_tiktok_only.py',    'TikTok'),
    'threads':   ('scraped_Threads_Only.csv',   'run_threads_only.py',   'Threads'),
    'facebook':  ('scraped_Facebook_Only.csv',  'run_facebook_only.py',  'Facebook')
}

# Alias pendek agar lebih praktis
ALIASES = {
    'x': 'twitter',
    'berita': 'news',
    'yt': 'youtube',
    'ig': 'instagram',
    'tt': 'tiktok',
    'th': 'threads',
    'fb': 'facebook',
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

def print_banner(platform_name, since_str, until_str):
    print("=" * 75)
    print("🎯 SCRAPER KEMEN PU: PERIODE 9 - 15 NOVEMBER 2026")
    print("=" * 75)
    print(f"📅 Target Tanggal     : {since_str} s.d. {until_str}")
    print(f"🌐 Platform           : {platform_name.upper()}")
    print(f"📁 Direktori Simpan   : {SCRAPE_DIR}")
    print(f"💾 Mode               : APPEND & DEDUPLIKASI (Data lama tetap utuh)")
    print("=" * 75)

def run_single_platform(platform_key, since_str=DEFAULT_SINCE, until_str=DEFAULT_UNTIL):
    # Resolve alias
    platform_key = ALIASES.get(platform_key.lower(), platform_key.lower())
    
    if platform_key not in PLATFORM_MAP:
        print(f"❌ Platform '{platform_key}' tidak dikenali.")
        print(f"   Pilihan: {', '.join(PLATFORM_MAP.keys())}, combine, all")
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

    # Hitung until+1 hari untuk query eksklusif (Twitter/Google 'until:' sifatnya < tanggal)
    try:
        dt_until = datetime.strptime(until_str, '%Y-%m-%d')
        until_plus_1 = (dt_until + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        until_plus_1 = until_str

    # Set Environment Variables agar runner langsung menyerap rentang 9-15 Nov
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["SCRAPE_SINCE"] = since_str
    env["SCRAPE_UNTIL"] = until_plus_1
    env["SCRAPE_TARGETED"] = "1"

    print(f"\n▶ Menjalankan scraping {display_name}...")
    cmd = [sys.executable, "-u", script_name]

    try:
        ret = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        total_after, in_range_after = count_platform_stats(csv_file, since_str, until_str)
        added = max(0, total_after - total_before)
        added_in_range = max(0, in_range_after - in_range_before)

        print("\n" + "-" * 65)
        print(f"✅ [SELESAI] {display_name}:")
        print(f"   - Data baru ditambahkan          : +{added:,} baris")
        print(f"   - Tambahan di rentang 9-15 Nov   : +{added_in_range:,} baris")
        print(f"   - Total akhir di {csv_file:<22} : {total_after:,} baris ({in_range_after:,} periode target)")
        print("-" * 65)
        return ret.returncode == 0
    except KeyboardInterrupt:
        print(f"\n⚠️ Proses scraping {display_name} dihentikan pengguna.")
        return False

def run_combine():
    """Menggabungkan seluruh CSV, auto-backup, dan mengupdate enriched_corpus_for_sna.parquet"""
    print("\n" + "=" * 70)
    print("🔄 1. MENGGABUNGKAN SEMUA HASIL SCRAPING (NLP Cleaning & Dedup)")
    print("=" * 70)
    combine_script = os.path.join(CELLS_DIR, 'run_combine_all.py')
    if os.path.exists(combine_script):
        cmd = [sys.executable, "-u", 'run_combine_all.py']
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        res = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        if res.returncode != 0:
            print("❌ Gagal saat menggabungkan CSV.")
            return False
    else:
        print(f"❌ Script combine tidak ditemukan di {combine_script}")
        return False

    print("\n" + "=" * 70)
    print("🤖 2. AUTO-BACKUP & UPDATE DATA DASHBOARD (INDOBERT ENRICHMENT)")
    print("=" * 70)
    pipeline_script = os.path.join(BASE_DIR, 'run_local_pipeline.py')
    if os.path.exists(pipeline_script):
        cmd_pipe = [sys.executable, "-u", 'run_local_pipeline.py']
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        subprocess.run(cmd_pipe, cwd=BASE_DIR, env=env)
        print("\n🎉 DATA DASHBOARD BERHASIL DIPERBARUI & DATA LAMA AMAN TERCADANGKAN!")
    else:
        print(f"[WARN] Script {pipeline_script} tidak ditemukan.")

def show_interactive_menu():
    print("=" * 75)
    print("🎯 PILIH PLATFORM SCRAPING (PERIODE: 9 s.d. 15 NOVEMBER 2026)")
    print("=" * 75)
    print("  [1] Twitter / X")
    print("  [2] Berita Online (Google News & Bing)")
    print("  [3] YouTube")
    print("  [4] Instagram")
    print("  [5] TikTok")
    print("  [6] Threads")
    print("  [7] Facebook")
    print("  [8] Combine & Update Dashboard (Auto-Backup + IndoBERT Enrichment)")
    print("  [9] Jalankan SEMUA Platform (1 s.d. 7) + Combine & Update Dashboard")
    print("  [0] Keluar")
    print("=" * 75)
    
    choice = input("Pilih nomor platform [1-9]: ").strip()
    mapping = {
        '1': 'twitter',
        '2': 'news',
        '3': 'youtube',
        '4': 'instagram',
        '5': 'tiktok',
        '6': 'threads',
        '7': 'facebook',
        '8': 'combine',
        '9': 'all'
    }
    return mapping.get(choice)

def main():
    parser = argparse.ArgumentParser(
        description="Runner Scraping Kemen PU Periode 9-15 November 2026",
        usage="python run_scrape_nov09_15.py [platform] [--since YYYY-MM-DD] [--until YYYY-MM-DD]"
    )
    parser.add_argument(
        'platform',
        nargs='?',
        default=None,
        help="Platform target: twitter, news, youtube, instagram, tiktok, threads, facebook, combine, all"
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
        help=f"Tanggal akhir (default: {DEFAULT_UNTIL})"
    )

    args = parser.parse_args()
    target_platform = args.platform

    # Jika dijalankan tanpa argumen, tampilkan menu interaktif
    if not target_platform:
        target_platform = show_interactive_menu()
        if not target_platform:
            print("Keluar.")
            return

    target_platform = ALIASES.get(target_platform.lower(), target_platform.lower())

    if target_platform == 'combine':
        run_combine()
        return

    if target_platform == 'all':
        print_banner("SEMUA PLATFORM", args.since, args.until)
        for p in PLATFORM_MAP.keys():
            run_single_platform(p, args.since, args.until)
        run_combine()
        print("\n🎉 SELURUH PLATFORM TELAH SELESAI DISCRAPE & DIGABUNGKAN!")
        return

    if target_platform in PLATFORM_MAP:
        print_banner(PLATFORM_MAP[target_platform][2], args.since, args.until)
        run_single_platform(target_platform, args.since, args.until)
        print(f"\n💡 Tips: Setelah selesai scraping, jalankan 'python run_scrape_nov09_15.py combine' untuk menggabungkan data.")
    else:
        print(f"❌ Pilihan tidak valid: {target_platform}")
        print(f"   Pilihan yang tersedia: {', '.join(PLATFORM_MAP.keys())}, combine, all")

if __name__ == '__main__':
    main()
