# ============================================================
# CELL 1: INSTALL DEPENDENCIES & SETUP ENVIRONMENT
# Jalankan cell ini pertama kali sebelum yang lain
# ============================================================

# YouTube (yt-dlp sebagai search engine, scrapetube sebagai alternatif)
!pip install -q yt-dlp scrapetube

# Twitter/X (twikit = cookie-based, tidak perlu API key)
!pip install -q twikit --upgrade
!pip install -q nest_asyncio

# TikTok, Facebook, Threads (Automasi Browser Async)
!pip install -q playwright playwright-stealth
!playwright install chromium
!playwright install-deps

# Google News (feedparser = ringan, cepat, tanpa rate-limit)
!pip install -q gnews feedparser newspaper3k lxml_html_clean

# Instagram (upgrade ke versi terbaru untuk menghindari error "out of date")
!pip install -q instagrapi --upgrade

# DuckDuckGo Search — fallback universal untuk semua platform
# Jauh lebih toleran terhadap IP datacenter (Colab) dibanding Google
!pip install -q ddgs

# Utilitas umum
!pip install -q pandas python-dotenv tqdm

# Pasang nest_asyncio agar async bisa jalan di dalam Jupyter/Colab
import nest_asyncio
nest_asyncio.apply()

# Mount Google Drive untuk menyimpan hasil
from google.colab import drive
drive.mount('/content/drive')

import os
OUTPUT_DIR = '/content/drive/MyDrive/ScrapeData'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Hapus session Instagram lama yang bisa menyebabkan error
ig_session = f'{OUTPUT_DIR}/ig_session.json'
if os.path.exists(ig_session):
    os.remove(ig_session)
    print("[INFO] Session Instagram lama dihapus (untuk login bersih)")

print("=" * 60)
print("[OK] SEMUA DEPENDENCIES TERINSTALL")
print(f"[INFO] Output folder: {OUTPUT_DIR}")
print("=" * 60)
