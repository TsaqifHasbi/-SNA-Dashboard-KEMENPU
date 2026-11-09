"""
================================================================================
🚀 RESCUE & ENRICHMENT UNTUK SELURUH PLATFORM (Twitter, Threads, Facebook, Instagram, TikTok)
================================================================================
Fungsi:
  Memeriksa seluruh baris yang caption-nya terindikasi terpotong (...) atau
  memiliki teks 'see more/lihat selengkapnya', lalu mengambil teks 100% lengkap
  langsung dari sumber API/OpenGraph/Selenium masing-masing platform.
================================================================================
"""

import os
import sys
import re
import json
import time
import html
import shutil
import urllib.request
from datetime import datetime
import pandas as pd

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE_DIR = os.path.join(WORKSPACE_DIR, 'ScrapeData')
COLAB_DIR = os.path.join(WORKSPACE_DIR, 'colab_cells')
sys.path.insert(0, COLAB_DIR)


def enrich_twitter(limit=None):
    csv_path = os.path.join(SCRAPE_DIR, 'scraped_Twitter_Only.csv')
    if not os.path.exists(csv_path):
        print("[ERROR] File Twitter tidak ditemukan!")
        return

    df = pd.read_csv(csv_path)
    mask = df['content'].astype(str).str.contains(r'(\.\.\.|…)\s*$|\b(see more|lihat selengkapnya)\b', regex=True, na=False)
    indices = df[mask].index.tolist()
    print(f"\n[TWITTER] Ditemukan {len(indices)} tweet terindikasi terpotong.")
    if not indices:
        return

    if limit:
        indices = indices[:limit]

    # Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(csv_path, os.path.join(SCRAPE_DIR, f'scraped_Twitter_Only_BEFORE_ENRICH_{ts}.csv'))

    fixed = 0
    for step, idx in enumerate(indices, 1):
        url = str(df.loc[idx, 'url'])
        old_c = str(df.loc[idx, 'content'])
        m = re.search(r'/status/(\d+)', url)
        if not m:
            continue
        tid = m.group(1)

        api_url = f'https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=5'
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                new_c = data.get('text', '')
                if 'note_tweet' in data:
                    try:
                        new_c = data['note_tweet']['note_tweet_results']['result']['text']
                    except:
                        pass
                new_clean = new_c.replace('\n', ' | ').strip()

                # Strict Guard: Hanya gantikan jika new_clean TIDAK KOSONG dan LEBIH PANJANG dari old_c
                if new_clean and len(new_clean) > len(old_c):
                    df.loc[idx, 'content'] = new_clean
                    fixed += 1
                    print(f"[{step}/{len(indices)}] [TWITTER EXPANDED] {len(old_c)} -> {len(new_clean)} char | ID: {tid}")
                else:
                    # Lewati jika sama panjang, lebih pendek, atau tweet sudah dihapus
                    pass
        except Exception:
            pass

        if step % 20 == 0 or step == len(indices):
            df.to_csv(csv_path, index=False)
            print(f"  [PROGRES] Memeriksa {step}/{len(indices)} tweet... ({fixed} diperluas sejauh ini)")
        time.sleep(0.2)

    df.to_csv(csv_path, index=False)
    print(f"\n[TWITTER SELESAI] Selesai memeriksa seluruh {len(indices)} tweet! Total {fixed} tweet berhasil diperluas.")


def enrich_threads(limit=None):
    csv_path = os.path.join(SCRAPE_DIR, 'scraped_Threads_Only.csv')
    if not os.path.exists(csv_path):
        print("[ERROR] File Threads tidak ditemukan!")
        return

    df = pd.read_csv(csv_path)
    mask = df['content'].astype(str).str.contains(r'(\.\.\.|…)\s*$|\b(see more|lihat selengkapnya)\b', regex=True, na=False)
    indices = df[mask].index.tolist()
    print(f"\n[THREADS] Ditemukan {len(indices)} postingan Threads terindikasi terpotong.")
    if not indices:
        return

    if limit:
        indices = indices[:limit]

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(csv_path, os.path.join(SCRAPE_DIR, f'scraped_Threads_Only_BEFORE_ENRICH_{ts}.csv'))

    fixed = 0
    for step, idx in enumerate(indices, 1):
        url = str(df.loc[idx, 'url'])
        old_c = str(df.loc[idx, 'content'])
        req = urllib.request.Request(url, headers={'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'})
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'<meta\s+property="og:description"\s+content="(.*?)"', content, re.DOTALL)
                if m:
                    new_c = html.unescape(m.group(1)).replace('\n', ' | ').strip()
                    # Strict Guard: Hanya gantikan jika new_c TIDAK KOSONG dan LEBIH PANJANG dari old_c
                    if new_c and len(new_c) > len(old_c):
                        df.loc[idx, 'content'] = new_c
                        fixed += 1
                        print(f"[{step}/{len(indices)}] [THREADS EXPANDED] {len(old_c)} -> {len(new_c)} char")
        except Exception:
            pass

        if step % 25 == 0 or step == len(indices):
            df.to_csv(csv_path, index=False)
            print(f"  [PROGRES] Memeriksa {step}/{len(indices)} threads... ({fixed} diperluas sejauh ini)")
        time.sleep(0.3)

    df.to_csv(csv_path, index=False)
    print(f"\n[THREADS SELESAI] Selesai memeriksa seluruh {len(indices)} threads! Total {fixed} postingan berhasil diperluas.")


def enrich_facebook(limit=None):
    from cell_09_facebook import enrich_single_facebook_post
    csv_path = os.path.join(SCRAPE_DIR, 'scraped_Facebook_Only.csv')
    if not os.path.exists(csv_path):
        print("[ERROR] File Facebook tidak ditemukan!")
        return

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    mask = df['content'].astype(str).str.contains(r'(\.\.\.|…)\s*$|\b(see more|lihat selengkapnya)\b', regex=True, na=False)
    indices = df[mask].index.tolist()
    print(f"\n[FACEBOOK] Ditemukan {len(indices)} postingan Facebook terindikasi terpotong.")
    if not indices:
        return

    if limit:
        indices = indices[:limit]

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(csv_path, os.path.join(SCRAPE_DIR, f'scraped_Facebook_Only_BEFORE_ENRICH_{ts}.csv'))

    fixed = 0
    for step, idx in enumerate(indices, 1):
        url = str(df.loc[idx, 'url'])
        old_c = str(df.loc[idx, 'content'])
        try:
            details = enrich_single_facebook_post(url)
            new_c = details.get('content', '')
            if new_c and len(new_c) > len(old_c):
                df.loc[idx, 'content'] = new_c.replace('\n', ' | ').strip()
                if details.get('created_at'):
                    df.loc[idx, 'created_at'] = details['created_at']
                fixed += 1
                print(f"[{step}/{len(indices)}] [FB EXPANDED] {len(old_c)} -> {len(new_c)} char | URL: {url[:50]}...")
        except Exception as e:
            print(f"[{step}/{len(indices)}] [FB ERROR] {e}")

        if step % 10 == 0:
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        time.sleep(1.5)

    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"[FACEBOOK SELESAI] Total {fixed} postingan Facebook berhasil diperluas!")


if __name__ == '__main__':
    plat = 'all'
    limit = None
    if len(sys.argv) > 1:
        plat = sys.argv[1].lower().replace('--', '')
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except:
            pass

    print("=" * 65)
    print(f"🛠️ MEMULAI ENRICHMENT MULTI-PLATFORM (Mode: {plat.upper()})")
    print("=" * 65)

    if plat in ['twitter', 'all']:
        enrich_twitter(limit=limit)
    if plat in ['threads', 'all']:
        enrich_threads(limit=limit)
    if plat in ['facebook', 'fb']:
        enrich_facebook(limit=limit)

    print("\n✅ Seluruh proses enrichment yang dipilih telah selesai!")
