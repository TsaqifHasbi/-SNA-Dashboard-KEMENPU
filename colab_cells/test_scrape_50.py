import os
import sys
import time
import json
import re
import random
from datetime import datetime, timezone, timedelta
import urllib.parse
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

WIB = timezone(timedelta(hours=7))
TIKTOK_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".tiktok_scraper_profile")

def parse_engagement(text):
    if not text:
        return 0
    text = text.lower().replace(' ', '').replace(',', '.')
    m = re.search(r'([\d.]+)\s*([kmrbjtribu]*)', text)
    if not m:
        return 0
    try:
        num = float(m.group(1))
    except:
        return 0
    suffix = m.group(2)
    if 'k' in suffix or 'rb' in suffix or 'ribu' in suffix:
        num *= 1000
    elif 'm' in suffix or 'jt' in suffix or 'juta' in suffix:
        num *= 1000000
    return int(num)

options = uc.ChromeOptions()
options.add_argument('--disable-popup-blocking')
options.add_argument('--disable-notifications')
options.add_argument('--lang=id-ID,id,en-US,en')
options.add_argument('--disable-background-timer-throttling')
options.add_argument('--disable-backgrounding-occluded-windows')
options.add_argument('--disable-renderer-backgrounding')
options.add_argument(f'--user-data-dir={TIKTOK_PROFILE_DIR}')

print("[TEST] Membuka browser Chrome untuk TikTok...")
driver = None
try:
    driver = uc.Chrome(options=options, version_main=154)
except Exception:
    try:
        driver = uc.Chrome(options=options, version_main=153)
    except Exception:
        driver = uc.Chrome(options=options)

keyword = "makan bergizi gratis"
query = urllib.parse.quote(keyword)
url = f"https://www.tiktok.com/search?q={query}"

print(f"[TEST] Membuka URL: {url}")
driver.get(url)
print("[TEST] Menunggu 8 detik halaman search termuat...")
time.sleep(8)

# Simpan HTML awal untuk analisis
html_source = driver.page_source
with open("test_search_page.html", "w", encoding="utf-8") as f:
    f.write(html_source)
print(f"[TEST] HTML awal tersimpan ({len(html_source)} bytes)")

# Cek apakah ada JSON rehydration
rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html_source, re.DOTALL)
sigi = re.search(r"window\['SIGI_STATE'\]=(.*?);window\[", html_source)
print(f"[TEST] Universal Data found: {bool(rehyd)}, SIGI found: {bool(sigi)}")

# Ekstrak video test
all_videos = {}
max_results = 50
scroll_count = 0

while len(all_videos) < max_results and scroll_count < 15:
    scroll_count += 1
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Cek DOM video links
    video_links = soup.find_all('a', href=lambda h: h and '/video/' in h)
    
    # Cek JSON
    json_count = 0
    if rehyd:
        try:
            jdata = json.loads(rehyd.group(1))
            def traverse(obj):
                if isinstance(obj, dict):
                    if 'stats' in obj and isinstance(obj['stats'], dict) and 'diggCount' in obj['stats']:
                        vid_id = str(obj.get('id', ''))
                        if vid_id and vid_id not in all_videos:
                            stats = obj['stats']
                            author_info = obj.get('author', {})
                            desc = obj.get('desc', '')
                            all_videos[vid_id] = {
                                'id': vid_id,
                                'source': 'json',
                                'author': author_info.get('nickname', '') or author_info.get('uniqueId', ''),
                                'handle': author_info.get('uniqueId', ''),
                                'content': re.sub(r'[\r\n]+', ' ', str(desc)).strip(),
                                'likes': int(stats.get('diggCount', 0)),
                                'comments': int(stats.get('commentCount', 0)),
                                'saves': int(stats.get('collectCount', 0)),
                                'shares': int(stats.get('shareCount', 0)),
                                'views': int(stats.get('playCount', 0)),
                                'url': f"https://www.tiktok.com/@{author_info.get('uniqueId', 'user')}/video/{vid_id}",
                            }
                    for v in obj.values():
                        if isinstance(v, (dict, list)):
                            traverse(v)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            traverse(item)
            traverse(jdata)
        except Exception as e:
            pass

    # DOM cards
    cards = soup.find_all('div', {'class': lambda x: x and 'DivItemContainer' in x})
    if not cards:
        cards = soup.find_all('div', {'data-e2e': 'search_top-item'})
    if not cards:
        cards = soup.find_all('div', {'data-e2e': 'search-common-link'})
    if not cards:
        cards = []
        for vl in video_links:
            p = vl.parent
            for _ in range(4):
                if p and p.name != 'body':
                    if p.get('data-e2e') or (p.get('class') and any('Item' in c or 'Card' in c for c in p.get('class'))):
                        cards.append(p)
                        break
                    p = p.parent
                else:
                    break
            else:
                cards.append(vl.parent)

    for card in cards:
        try:
            link = card.find('a', href=lambda h: h and '/video/' in h)
            if not link:
                continue
            v_url = link['href']
            if not v_url.startswith('http'):
                v_url = 'https://www.tiktok.com' + v_url
            
            m_id = re.search(r'/video/(\d+)', v_url)
            if not m_id:
                continue
            vid_id = m_id.group(1)
            if vid_id in all_videos:
                continue

            # Handle & Author
            m_handle = re.search(r'@([^/?&#]+)', v_url)
            handle = m_handle.group(1) if m_handle else ""
            author_tag = card.find('span', {'data-e2e': 'search-card-user-nickname'}) or card.find('p', {'data-e2e': 'search-card-user-nickname'})
            author = author_tag.text.strip() if author_tag else handle

            # Views
            views_tag = card.find('strong', {'data-e2e': 'video-views'}) or card.find('div', {'data-e2e': 'video-views'})
            views = parse_engagement(views_tag.text.strip()) if views_tag else 0

            # Likes (jika ada di card)
            like_tag = card.find(attrs={'data-e2e': lambda x: x and 'like' in x})
            likes = parse_engagement(like_tag.text.strip()) if like_tag else 0

            # Saves/Collect (jika ada di card)
            save_tag = card.find(attrs={'data-e2e': lambda x: x and ('collect' in x or 'save' in x or 'favorite' in x)})
            saves = parse_engagement(save_tag.text.strip()) if save_tag else 0

            # Caption
            cap_tag = card.find('div', {'data-e2e': 'search-card-video-caption'}) or card.find('div', {'class': lambda x: x and 'DivTextContainer' in x})
            caption = cap_tag.text.strip() if cap_tag else ""

            all_videos[vid_id] = {
                'id': vid_id,
                'source': 'dom',
                'author': author,
                'handle': handle,
                'content': re.sub(r'[\r\n]+', ' ', caption).strip(),
                'likes': likes,
                'comments': 0,
                'saves': saves,
                'shares': 0,
                'views': views,
                'url': v_url,
            }
        except:
            pass

    print(f"  [Scroll {scroll_count}] Total video terkumpul: {len(all_videos)}")

    # Dismiss modal if present
    try:
        close_btn = driver.find_elements(By.CSS_SELECTOR, 'div[data-e2e="modal-close-inner-button"], [aria-label="Close"], button[class*="close"]')
        if close_btn:
            close_btn[0].click()
    except Exception:
        pass

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(2.5, 3.5))

print(f"\n[HASIL TEST] Selesai scroll! Total {len(all_videos)} video berhasil diekstrak.")

# Tampilkan sample 5 data
print("\n--- SAMPLE 5 DATA TIKTOK ---")
for i, (vid_id, v) in enumerate(list(all_videos.items())[:5]):
    print(f"\nData #{i+1}:")
    print(f"  Author  : {v['author']} (@{v['handle']})")
    print(f"  URL     : {v['url']}")
    print(f"  Content : {v['content'][:100]}...")
    print(f"  Views   : {v['views']}")
    print(f"  Likes   : {v['likes']}")
    print(f"  Comments: {v['comments']}")
    print(f"  Saves   : {v['saves']}")
    print(f"  Shares  : {v['shares']}")
    print(f"  Source  : {v['source']}")

# Statistik Metrik
has_views = sum(1 for v in all_videos.values() if v['views'] > 0)
has_likes = sum(1 for v in all_videos.values() if v['likes'] > 0)
has_comments = sum(1 for v in all_videos.values() if v['comments'] > 0)
has_saves = sum(1 for v in all_videos.values() if v['saves'] > 0)
has_shares = sum(1 for v in all_videos.values() if v['shares'] > 0)

print("\n" + "="*50)
print("STATISTIK METRIK YANG DIDAPAT (DARI TOTAL " + str(len(all_videos)) + " DATA):")
print(f"  - Views > 0    : {has_views} video ({has_views/len(all_videos)*100 if all_videos else 0:.1f}%)")
print(f"  - Likes > 0    : {has_likes} video ({has_likes/len(all_videos)*100 if all_videos else 0:.1f}%)")
print(f"  - Comments > 0 : {has_comments} video ({has_comments/len(all_videos)*100 if all_videos else 0:.1f}%)")
print(f"  - Saves > 0    : {has_saves} video ({has_saves/len(all_videos)*100 if all_videos else 0:.1f}%)")
print(f"  - Shares > 0   : {has_shares} video ({has_shares/len(all_videos)*100 if all_videos else 0:.1f}%)")
print("="*50)

# Simpan ke test CSV
import pandas as pd
df_test = pd.DataFrame(list(all_videos.values()))
df_test.to_csv("test_50_tiktok.csv", index=False, encoding='utf-8-sig')
print(f"[OK] File tersimpan ke test_50_tiktok.csv")

driver.quit()
