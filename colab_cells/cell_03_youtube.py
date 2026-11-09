from cell_02_config import *
# ============================================================
# CELL 3: SCRAPER YOUTUBE
# Tools: YouTube Data API v3 (Utama)
# Fallback: scrapetube & yt-dlp search
# Target: ~100 video per keyword
# ============================================================

# pyrefly: ignore [missing-import]
import scrapetube
import subprocess
import json
import time
import re
import requests
from datetime import datetime

import sys
# Resolve API Key dari Colab (__main__) atau local import
try:
    from cell_02_config import YOUTUBE_API_KEYS as _yt_keys_pool
except ImportError:
    _yt_keys_pool = []

if not _yt_keys_pool:
    try:
        from cell_02_config import YOUTUBE_API_KEY as _single_k
        if _single_k and _single_k != "YOUR_YOUTUBE_API_KEY_HERE" and _single_k != "PASTE_YOUTUBE_API_KEY_DI_SINI":
            _yt_keys_pool = [_single_k]
    except Exception:
        _yt_keys_pool = []

_current_key_idx = 0

def get_current_yt_key():
    global _current_key_idx, _yt_keys_pool
    if _yt_keys_pool and _current_key_idx < len(_yt_keys_pool):
        return _yt_keys_pool[_current_key_idx]
    return getattr(sys.modules['__main__'], 'YOUTUBE_API_KEY', None)

def rotate_yt_key():
    global _current_key_idx, _yt_keys_pool
    if _yt_keys_pool and _current_key_idx + 1 < len(_yt_keys_pool):
        _current_key_idx += 1
        new_k = _yt_keys_pool[_current_key_idx]
        print(f"\n    🔄 [KEY ROTATION] Berpindah ke YouTube API Key #{_current_key_idx + 1} ({new_k[:10]}...)")
        return new_k
    return None

def parse_view_count(text):
    """Mengubah teks views YouTube menjadi integer."""
    if not text:
        return 0
    text = str(text).lower().replace(',', '').replace('.', '')
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else 0

# ============================================================
# UTAMA: Menggunakan YouTube Data API v3 Resmi
# ============================================================
# Flag global: jika API v3 sudah kehabisan kuota, langsung pakai scrapetube
_yt_api_exhausted = False

def scrape_youtube_api(keyword, max_results=100):
    """
    Mengambil data dari YouTube menggunakan API Resmi v3 dari Google.
    Ini adalah cara paling stabil dan menghasilkan data yang sangat bersih.
    """
    global _yt_api_exhausted
    
    # Jika sudah pernah kena 429, langsung skip ke fallback
    if _yt_api_exhausted:
        return None
    
    api_key = get_current_yt_key()
    if not api_key or api_key == "PASTE_YOUTUBE_API_KEY_DI_SINI":
        print("    [!] YOUTUBE_API_KEY belum diisi di Cell 2 atau .env.")
        return None  # Return None agar otomatis masuk fallback

    results = []
    try:
        search_url = "https://www.googleapis.com/youtube/v3/search"
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        
        # 1. Cari video (Search API)
        video_ids = []
        snippets = {}
        
        per_page = min(50, max_results)  # API max 50 per request
        since_env = os.environ.get('SCRAPE_SINCE')
        until_env = os.environ.get('SCRAPE_UNTIL')
        pub_after = f"{since_env}T00:00:00Z" if since_env else "2025-01-01T00:00:00Z"
        
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": per_page,
            "publishedAfter": pub_after,
            "key": api_key
        }
        if until_env:
            params["publishedBefore"] = f"{until_env}T23:59:59Z"
        
        while len(video_ids) < max_results:
            res = requests.get(search_url, params=params)
            if res.status_code != 200:
                err_msg = res.text[:100]
                print(f"    [!] Error API v3 (Search): {res.status_code} - {err_msg}")
                if res.status_code == 429 or "Quota exceeded" in res.text or "quotaExceeded" in res.text or res.status_code == 403:
                    new_key = rotate_yt_key()
                    if new_key:
                        api_key = new_key
                        params["key"] = new_key
                        continue

                    _yt_api_exhausted = True
                    print("\n" + "="*60)
                    print("🚨 SELURUH KUOTA API YOUTUBE HABIS! 🚨")
                    print("Batas token harian YouTube Data API telah tercapai (HTTP 403 Quota Exceeded).")
                    print("Proses dihentikan agar data sebelumnya bisa tersimpan.")
                    print("API YouTube akan reset pada TENGAH MALAM waktu Pasifik (Pacific Time / PT).")
                    print("Atau sekitar jam 14:00 WIB / 15:00 WIB keesokan harinya.")
                    print("Silakan jalankan ulang script ini setelah jam tersebut untuk melanjutkan.")
                    print("="*60 + "\n")
                    # Jangan sys.exit, raise exception agar runner bisa save data
                    raise SystemExit("YouTube API quota exhausted")
                return None
                
            data = res.json()
            items = data.get("items", [])
            if not items:
                break
                
            for item in items:
                vid = item["id"]["videoId"]
                video_ids.append(vid)
                snippets[vid] = item["snippet"]
            
            print(f"      [API] {len(video_ids)} video ID terkumpul...")
                    
            # Stop jika sudah cukup
            if len(video_ids) >= max_results:
                video_ids = video_ids[:max_results]
                break
                
            # Pagination
            if "nextPageToken" in data:
                params["pageToken"] = data["nextPageToken"]
            else:
                break
                
        if not video_ids:
            return []

        # 2. Ambil statistik views & likes (Videos API)
        # Pisahkan menjadi batch 50
        stats = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            v_params = {
                "part": "statistics,contentDetails",
                "id": ",".join(batch),
                "key": api_key
            }
            v_res = requests.get(videos_url, params=v_params)
            if v_res.status_code == 200:
                v_data = v_res.json()
                for v_item in v_data.get("items", []):
                    stats[v_item["id"]] = v_item
            else:
                print(f"    [!] Error API v3 (Videos): {v_res.status_code}")

        # 3. Gabungkan data
        for vid in video_ids:
            snip = snippets.get(vid, {})
            stat_item = stats.get(vid, {})
            st = stat_item.get("statistics", {})
            cd = stat_item.get("contentDetails", {})
            
            results.append({
                "post_id": vid,
                "platform": "YouTube",
                "author": snip.get("channelTitle", ""),
                "handle": snip.get("channelId", ""),
                "content": snip.get("title", ""),
                "description": snip.get("description", ""),
                "created_at": snip.get("publishedAt", ""),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "views": int(st.get("viewCount", 0)),
                "views_text": str(st.get("viewCount", 0)),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url", ""),
                "duration": cd.get("duration", ""),
                "keyword": keyword,
                "scraped_at": datetime.now().isoformat()
            })

    except Exception as e:
        print(f"    [!] YouTube API error untuk '{keyword}': {str(e)[:100]}")
        return None

    return results

# ============================================================
# FALLBACK 1: Menggunakan scrapetube
# ============================================================
def scrape_youtube_scrapetube(keyword, max_results=100):
    results = []
    try:
        videos = scrapetube.get_search(keyword, limit=max_results)
        for video in videos:
            if len(results) >= max_results:
                break
            
            video_id = video.get("videoId", "")
            title_data = video.get("title", {})
            title = title_data.get("runs", [{"text": ""}])[0].get("text", "") if isinstance(title_data, dict) else ""
            
            views = 0
            vct = video.get("viewCountText", {})
            if isinstance(vct, dict):
                views = parse_view_count(vct.get("simpleText", "0"))
                
            channel_info = video.get("ownerText", {})
            channel_name = ""
            if isinstance(channel_info, dict) and channel_info.get("runs"):
                channel_name = channel_info["runs"][0].get("text", "")
                
            pub_data = video.get("publishedTimeText", {})
            published = pub_data.get("simpleText", "") if isinstance(pub_data, dict) else ""
            
            if not title: continue
            
            results.append({
                "post_id": video_id or f"yt_{len(results)}",
                "platform": "YouTube",
                "author": channel_name,
                "handle": "",
                "content": title,
                "description": "",
                "created_at": published,
                "likes": 0,
                "comments": 0,
                "views": views,
                "views_text": str(views),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                "thumbnail": "",
                "duration": "",
                "keyword": keyword,
                "scraped_at": datetime.now().isoformat()
            })
        time.sleep(1)
    except Exception as e:
        print(f"    [!] scrapetube error: {str(e)[:100]}")
    return results

# ============================================================
# ORKESTRATOR YOUTUBE (Fungsi Utama)
# ============================================================
def scrape_youtube(keyword, max_results=100):
    """
    Fungsi ini akan otomatis mencoba API Resmi v3 terlebih dahulu.
    Jika gagal (API Key salah/limit/kosong), otomatis pindah ke fallback (scrapetube).
    """
    # Coba Lapis 1: API Resmi
    api_results = scrape_youtube_api(keyword, max_results)
    
    if api_results is not None:
        return api_results
        
    # Coba Lapis 2: scrapetube
    #print(f"    [INFO] Beralih ke fallback (scrapetube) untuk '{keyword}'...")
    return scrape_youtube_scrapetube(keyword, max_results)

# ============================================================
# TEST (hanya jalan kalau dieksekusi langsung, bukan saat import)
# ============================================================
if __name__ == "__main__":
    print("[TEST] Menguji YouTube scraper...")
    _test_api_key = _yt_key
    if _test_api_key and _test_api_key != "PASTE_YOUTUBE_API_KEY_DI_SINI":
        print("[INFO] Menggunakan jalur API v3 Resmi")
    else:
        print("[INFO] Menggunakan jalur Fallback (API Key tidak ditemukan)")

    test = scrape_youtube("Kementerian Pekerjaan Umum", max_results=5)
    print(f"[OK] YouTube: {len(test)} video ditemukan")

    for t in test[:3]:
        print(f"   [VIDEO] {t['content'][:70]}...")
        print(f"      Author: {t['author']} | Views: {t['views']} | URL: {t['url'][:60]}")
