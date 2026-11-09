import os
import sys
import argparse

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# AKTIFKAN MODE TA ELEKTRIFIKASI SEBELUM IMPORT
os.environ['PROJECT_MODE'] = 'ELEKTRIFIKASI'
if '--ta' not in sys.argv:
    sys.argv.append('--ta')

# Pastikan path modul terbaca
cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from cell_02_config_elektrifikasi import TOPICS, OUTPUT_DIR

PLATFORMS = {
    'facebook': 'run_facebook_only.py',
    'instagram': 'run_instagram_only.py',
    'twitter': 'run_twitter_only.py',
    'tiktok': 'run_tiktok_only.py',
    'threads': 'run_threads_only.py',
    'youtube': 'run_youtube_only.py',
    'news': 'run_news_only.py'
}

def print_banner(platform_name=None):
    print("=" * 65)
    print("⚡ SCRAPER KHUSUS TUGAS AKHIR (TA): ELEKTRIFIKASI KENDARAAN")
    print("=" * 65)
    print(f"📁 Folder Penyimpanan : {OUTPUT_DIR}")
    print(f"🎯 Objek Penelitian    : 1. Elektrifikasi_Kendaraan (Ekosistem, Kebijakan, SPKLU)")
    print(f"                        2. Mobil_Listrik (EV Roda 4, Insentif, Subsidi)")
    print(f"                        3. Motor_Listrik (EV Roda 2, Subsidi, Konversi)")
    total_kws = sum(len(v) for v in TOPICS.values())
    print(f"📊 Total Keywords     : {total_kws} variasi kata kunci")
    if platform_name:
        print(f"🌐 Platform Target    : {platform_name.upper()}")
    print("=" * 65)

def run_platform(platform_name):
    import subprocess
    platform_name = platform_name.lower().strip()
    if platform_name not in PLATFORMS:
        print(f"[ERROR] Platform '{platform_name}' tidak dikenal.")
        print(f"        Pilihan: {', '.join(PLATFORMS.keys())} atau 'all'")
        return

    script_name = PLATFORMS[platform_name]
    script_path = os.path.join(cur_dir, script_name)
    
    print_banner(platform_name)
    print(f"\n🚀 Menjalankan script: {script_name}...")
    
    cmd = [sys.executable, "-u", script_path, "--ta"]
    env = os.environ.copy()
    env["PROJECT_MODE"] = "ELEKTRIFIKASI"
    env["PYTHONUNBUFFERED"] = "1"
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print(f"\n[!] Scraping {platform_name.upper()} dihentikan oleh user (Ctrl+C).")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Master Runner Scraper TA Elektrifikasi Kendaraan")
    parser.add_argument('--platform', type=str, default='all',
                        help="Pilih platform: facebook, instagram, twitter, tiktok, threads, youtube, news, atau all")
    
    args, unknown = parser.parse_known_args()
    target_platform = args.platform.lower().strip()
    
    if target_platform == 'all':
        print_banner("ALL 7 PLATFORMS")
        for p in PLATFORMS.keys():
            print(f"\n{'#' * 60}\n# MULAI SCRAPING: {p.upper()}\n{'#' * 60}")
            run_platform(p)
    else:
        run_platform(target_platform)
