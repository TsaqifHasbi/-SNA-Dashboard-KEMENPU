"""
================================================================================
🎯 TARGETED DATE RANGE SCRAPER - KEMENTERIAN PEKERJAAN UMUM RI (KEMEN PU)
================================================================================
Scraper khusus untuk memfokuskan penarikan data pada rentang tanggal tertentu
(Default: 31 Oktober 2026 s.d. 9 November 2026) untuk 7 platform data:
  1. Twitter / X      (Native operator: since:YYYY-MM-DD until:YYYY-MM-DD)
  2. News             (Google News RSS: after:YYYY-MM-DD before:YYYY-MM-DD)
  3. YouTube          (YouTube API v3: publishedAfter & publishedBefore)
  4. Instagram        (Google Dorking site:instagram.com/p/ + date range)
  5. Threads          (Google Dorking site:threads.net/@ + date range)
  6. TikTok           (Google Dorking site:tiktok.com/@ + date range)
  7. Facebook         (Google Dorking site:facebook.com + date range)

Fitur Utama:
  - LANGSUNG MENAMBAH (APPEND) ke CSV platform masing-masing di ScrapeData/
  - Deduplikasi URL otomatis (postingan lama tidak tertimpa/hilang)
  - Otomatis memperbarui ringkasan data sebelum dan sesudah scraping
  - Opsi langsung menggabungkan ke scraped_ALL_combined.csv

Penggunaan:
  python run_targeted_date_scrape.py --platform instagram
  python run_targeted_date_scrape.py --platform twitter
  python run_targeted_date_scrape.py --platform news
  python run_targeted_date_scrape.py --platform all
  python run_targeted_date_scrape.py --since 2026-10-31 --until 2026-11-09 --platform all
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

PLATFORM_MAP = {
    'twitter': ('scraped_Twitter_Only.csv', 'run_twitter_only.py'),
    'news': ('scraped_News_Only.csv', 'run_news_only.py'),
    'youtube': ('scraped_YouTube_Only.csv', 'run_youtube_only.py'),
    'instagram': ('scraped_Instagram_Only.csv', 'run_instagram_only.py'),
    'threads': ('scraped_Threads_Only.csv', 'run_threads_only.py'),
    'tiktok': ('scraped_TikTok_Only.csv', 'run_tiktok_only.py'),
    'facebook': ('scraped_Facebook_Only.csv', 'run_facebook_only.py')
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
    print("🎯 SCRAPER TARGETED DATE RANGE KEMEN PU")
    print("=" * 75)
    print(f"📅 Rentang Tanggal Target : {since_str} s.d. {until_str}")
    print(f"🌐 Platform Target         : {platform_name.upper()}")
    print(f"📁 Folder Penyimpanan      : {SCRAPE_DIR}")
    print(f"💾 Mode Simpan             : APPEND & DEDUP (Menambah data baru ke CSV lama)")
    print("=" * 75)

def run_targeted_platform(platform_key, since_str, until_str):
    if platform_key not in PLATFORM_MAP:
        print(f"❌ Platform '{platform_key}' tidak dikenali.")
        return False

    csv_file, script_name = PLATFORM_MAP[platform_key]
    script_path = os.path.join(CELLS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"❌ File runner tidak ditemukan: {script_path}")
        return False

    # Hitung data sebelum
    total_before, in_range_before = count_platform_stats(csv_file, since_str, until_str)
    print(f"\n📊 [STATUS AWAL] {csv_file}:")
    print(f"   - Total Data di CSV        : {total_before:,} baris")
    print(f"   - Data dalam Rentang Target: {in_range_before:,} baris")

    # Hitung until+1 hari untuk operator query (Twitter/Google 'until:' bersifat eksklusif)
    try:
        dt_until = datetime.strptime(until_str, '%Y-%m-%d')
        until_plus_1 = (dt_until + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        until_plus_1 = until_str

    # Set Environment Variables agar runner & scraper menangkap filter tanggal
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["SCRAPE_SINCE"] = since_str
    env["SCRAPE_UNTIL"] = until_plus_1
    env["SCRAPE_TARGETED"] = "1"

    print(f"\n▶ Menjalankan scraper {platform_key.upper()}...")
    cmd = [sys.executable, "-u", script_name]

    try:
        ret = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        total_after, in_range_after = count_platform_stats(csv_file, since_str, until_str)
        added = max(0, total_after - total_before)
        added_in_range = max(0, in_range_after - in_range_before)

        print("\n" + "-" * 60)
        print(f"✅ [HASIL SELESAI] {platform_key.upper()}:")
        print(f"   - Data baru berhasil ditambahkan : +{added:,} baris")
        print(f"   - Pertambahan di rentang target  : +{added_in_range:,} baris")
        print(f"   - Total Akhir di {csv_file:<22}: {total_after:,} baris ({in_range_after:,} dalam rentang {since_str} s.d. {until_str})")
        print("-" * 60)
        return ret.returncode == 0
    except KeyboardInterrupt:
        print(f"\n⚠️ Scraping {platform_key.upper()} dihentikan oleh user.")
        return False

def combine_all_datasets():
    """Menggabungkan semua CSV ke scraped_ALL_combined.csv"""
    print("\n" + "=" * 65)
    print("🔄 MENGGABUNGKAN SEMUA CSV KE SCRAPED_ALL_COMBINED.CSV")
    print("=" * 65)
    combine_script = os.path.join(CELLS_DIR, 'run_combine_all.py')
    if os.path.exists(combine_script):
        cmd = [sys.executable, "-u", 'run_combine_all.py']
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        subprocess.run(cmd, cwd=CELLS_DIR, env=env)
    else:
        print(f"❌ Script combine tidak ditemukan di {combine_script}")

def main():
    parser = argparse.ArgumentParser(description="Targeted Date Range Scraper Kemen PU")
    parser.add_argument('--platform', type=str, default='all', 
                        choices=list(PLATFORM_MAP.keys()) + ['all'],
                        help="Platform target (twitter, news, youtube, instagram, tiktok, threads, facebook, all)")
    parser.add_argument('--since', type=str, default='2026-10-31', 
                        help="Tanggal awal (format: YYYY-MM-DD), default: 2026-10-31")
    parser.add_argument('--until', type=str, default='2026-11-09', 
                        help="Tanggal akhir (format: YYYY-MM-DD), default: 2026-11-09")
    parser.add_argument('--no-combine', action='store_true',
                        help="Jangan jalankan run_combine_all.py setelah scraping selesai")
    
    args = parser.parse_args()

    print_banner(args.platform, args.since, args.until)

    platforms = list(PLATFORM_MAP.keys()) if args.platform == 'all' else [args.platform]

    for p in platforms:
        print(f"\n{'#'*65}\n# TARGETED SCRAPE: {p.upper()} ({args.since} s.d. {args.until})\n{'#'*65}")
        run_targeted_platform(p, args.since, args.until)

    if not args.no_combine:
        combine_all_datasets()

    print("\n" + "=" * 75)
    print("🎉 SEMUA PROSES TARGETED DATE SCRAPING TELAH SELESAI!")
    print(f"Seluruh CSV platform di folder ScrapeData/ sudah diperbarui.")
    print("=" * 75)

if __name__ == '__main__':
    main()

