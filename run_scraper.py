"""
================================================================================
🚀 CENTRAL SCRAPER CONTROLLER - KEMENTERIAN PEKERJAAN UMUM RI (KEMEN PU)
================================================================================
Central runner untuk menjalankan scraper 7 platform data:
1. YouTube Data API v3 & fallback
2. News (Google News RSS & Bing News RSS)
3. Twitter / X (Undetected Selenium)
4. TikTok (Undetected Selenium + API Interceptor)
5. Instagram (Undetected Selenium Multi-Source)
6. Threads (Undetected Selenium DOM Extractor)
7. Facebook (Undetected Selenium)

Penggunaan via Terminal:
  python run_scraper.py news        -> Jalankan News scraper
  python run_scraper.py youtube     -> Jalankan YouTube scraper
  python run_scraper.py twitter     -> Jalankan Twitter/X scraper
  python run_scraper.py tiktok      -> Jalankan TikTok scraper
  python run_scraper.py instagram   -> Jalankan Instagram scraper
  python run_scraper.py threads     -> Jalankan Threads scraper
  python run_scraper.py facebook    -> Jalankan Facebook scraper
  python run_scraper.py combine     -> Gabung & bersihkan semua CSV (NLP Cleaning)
  python run_scraper.py all         -> Jalankan scraping ke-7 platform bertahap + combine

Output Data:
  Seluruh hasil scraping tersimpan di:
  d:\\Project_Streamlit\\IndoBERT_SNA_MT_KEMENPU\\ScrapeData\\
================================================================================
"""

import os
import sys
import subprocess

# Set encoding untuk console Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CELLS_DIR = os.path.join(BASE_DIR, 'colab_cells')

PLATFORM_SCRIPTS = {
    'news': 'run_news_only.py',
    'youtube': 'run_youtube_only.py',
    'twitter': 'run_twitter_only.py',
    'tiktok': 'run_tiktok_only.py',
    'instagram': 'run_instagram_only.py',
    'threads': 'run_threads_only.py',
    'facebook': 'run_facebook_only.py',
    'combine': 'run_combine_all.py'
}

def print_banner():
    print("=" * 75)
    print("🚀 CONTROLLER SCRAPER 7 PLATFORM - KEMENTERIAN PEKERJAAN UMUM RI")
    print("=" * 75)
    print("Topik Penelitian:")
    print("  1. Kementerian_PU : Kementerian Pekerjaan Umum / Kemen PU RI")
    print("  2. Menteri_PU     : Menteri Pekerjaan Umum (Ir. Dody Hanggodo, M.P.E.)")
    print("-" * 75)
    print("Daftar perintah yang didukung:")
    for key, script in PLATFORM_SCRIPTS.items():
        print(f"  • {key:<12} -> colab_cells/{script}")
    print("  • all          -> Jalankan seluruh platform (1 s/d 7) lalu combine")
    print("  • targeted     -> Jalankan Targeted Date Scraper (Rentang 31 Okt - 9 Nov 2026)")
    print("=" * 75)

def run_script(script_name, title=""):
    target_path = os.path.join(CELLS_DIR, script_name)
    if not os.path.exists(target_path):
        print(f"❌ File script tidak ditemukan: {target_path}")
        return False
        
    print(f"\n▶ Menjalankan {title or script_name}...")
    cmd = [sys.executable, "-u", script_name]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        ret = subprocess.run(cmd, cwd=CELLS_DIR, env=env)
        return ret.returncode == 0
    except KeyboardInterrupt:
        print(f"\n⚠️ Proses dihentikan oleh user (Ctrl+C).")
        return False

def run_platform(platform_name):
    platform_name = platform_name.lower().strip()
    
    if platform_name == 'all':
        print("\n🚀 Memulai Eksekusi Scraping 7 Platform Lengkap...")
        platforms_to_run = ['news', 'youtube', 'twitter', 'tiktok', 'instagram', 'threads', 'facebook']
        for p in platforms_to_run:
            print(f"\n{'#'*65}\n# MULAI SCRAPING: {p.upper()}\n{'#'*65}")
            run_script(PLATFORM_SCRIPTS[p], f"SCRAPER {p.upper()}")
        print(f"\n{'#'*65}\n# MENGGABUNGKAN SELURUH DATASET HASIL SCRAPING\n{'#'*65}")
        run_script(PLATFORM_SCRIPTS['combine'], "COMBINE ALL DATA")
        return True
        
    if platform_name in ['targeted', 'date', 'dates']:
        print("\n🎯 Memulai Targeted Date Scraper (31 Okt - 9 Nov 2026)...")
        target_script = os.path.join(BASE_DIR, 'run_targeted_date_scrape.py')
        cmd = [sys.executable, "-u", target_script]
        ret = subprocess.run(cmd)
        return ret.returncode == 0

    if platform_name not in PLATFORM_SCRIPTS:
        print(f"❌ Platform '{platform_name}' tidak dikenal!")
        print(f"Pilihan yang tersedia: {', '.join(PLATFORM_SCRIPTS.keys())}, all")
        return False
        
    return run_script(PLATFORM_SCRIPTS[platform_name], f"{platform_name.upper()}")

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().strip()
        if arg in ['-h', '--help', 'help']:
            print_banner()
            sys.exit(0)
        run_platform(arg)
    else:
        print_banner()
        print("\nPilih nomor / nama platform untuk dijalankan:")
        options = list(PLATFORM_SCRIPTS.keys()) + ['all', 'targeted']
        for idx, opt in enumerate(options, 1):
            print(f"  [{idx}] {opt.upper()}")
        print("  [0] Keluar")
        
        try:
            choice = input("\nMasukkan pilihan: ").strip().lower()
            if choice in ['0', 'q', 'exit', 'keluar', '']:
                print("Operasi dibatalkan.")
                return
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                chosen_opt = options[int(choice) - 1]
            else:
                chosen_opt = choice
            run_platform(chosen_opt)
        except (KeyboardInterrupt, EOFError):
            print("\nOperasi dibatalkan.")

if __name__ == '__main__':
    main()
