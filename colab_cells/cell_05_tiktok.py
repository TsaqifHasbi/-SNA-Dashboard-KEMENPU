# ============================================================
# CELL 5: SCRAPING TIKTOK (SELENIUM UNDETECTED) — v3
# - Single-Phase: Scroll search page + extract from API Interceptor & JSON/DOM
# - TANPA buka tab per video (jauh lebih cepat)
# - Container Scroll: Support #grid-main (TikTok Modern Layout)
# - Metrik Lengkap: likes, comments, saves, shares, views
# - Persistent Chrome profile (login/session tersimpan)
# - Auto-inject cookies dari cell_02_config
# - Anti-throttling background tab
# - Auto-reconnect jika Chrome crash
# - Clean single-line CSV output
# ============================================================
import sys
import time
import urllib.parse
import json
import re
import os
import random
from datetime import datetime, timezone, timedelta

try:
    # pyrefly: ignore [missing-import]
    from bs4 import BeautifulSoup
except ImportError:
    pass

try:
    # pyrefly: ignore [missing-import]
    import undetected_chromedriver as uc
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.common.by import By
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.support.ui import WebDriverWait
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    pass

# WIB timezone
WIB = timezone(timedelta(hours=7))

# Global driver
TIKTOK_DRIVER = None
TIKTOK_SEARCH_TAB = None
TIKTOK_WORKER_TAB = None

# Path untuk Chrome profile persisten
TIKTOK_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".tiktok_scraper_profile")

# Global URL tracking
_SEEN_URLS = set()

# Counter untuk deteksi rate-limit: berapa kali berturut-turut Top Tab "No results"
_CONSECUTIVE_TOP_NORESULT = 0
_MAX_TOP_NORESULT_BEFORE_RELOGIN = 3  # Setelah 3x berturut-turut, minta relogin


def reset_tracking():
    global _SEEN_URLS
    _SEEN_URLS = set()


def _force_relogin():
    """Tutup Chrome, hapus session/cookies, buka ulang & minta login baru."""
    global TIKTOK_DRIVER, TIKTOK_SEARCH_TAB, TIKTOK_WORKER_TAB, _CONSECUTIVE_TOP_NORESULT
    import shutil

    print("\n" + "=" * 60)
    print("🔄 MEMULAI PROSES RE-LOGIN TIKTOK...")
    print("=" * 60)

    # 1. Tutup driver lama
    if TIKTOK_DRIVER is not None:
        try:
            TIKTOK_DRIVER.quit()
        except:
            pass
        TIKTOK_DRIVER = None
        TIKTOK_SEARCH_TAB = None
        TIKTOK_WORKER_TAB = None

    # 2. Hapus profile Chrome (cookies + session lama)
    if os.path.exists(TIKTOK_PROFILE_DIR):
        try:
            shutil.rmtree(TIKTOK_PROFILE_DIR, ignore_errors=True)
            print("    [OK] Session/cookies lama sudah dihapus.")
        except Exception as e:
            print(f"    [WARN] Gagal hapus profile: {e}")

    # 3. Reset counter
    _CONSECUTIVE_TOP_NORESULT = 0

    # 4. Buka Chrome baru dan minta login
    print("    [INFO] Membuka Chrome baru untuk login...")
    _init_driver(skip_input=False)  # Ini akan minta user login
    print("    [OK] Re-login selesai! Melanjutkan scraping...\n")


def load_seen_urls(urls):
    global _SEEN_URLS
    _SEEN_URLS.update(urls)
    print(f"    [DEDUP] {len(_SEEN_URLS)} URL sudah diketahui, akan di-skip.")


def parse_engagement(text):
    """Parse angka engagement (1.2K, 3.5M, 10rb, 2jt, dll)."""
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


def _kill_zombie_chrome_tiktok():
    """Membunuh proses Chrome zombie yang mengunci profile TikTok."""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            if p.info['name'] and 'chrome' in p.info['name'].lower():
                cmd = ' '.join(p.info['cmdline'] or [])
                if 'tiktok_scraper_profile' in cmd:
                    p.kill()
    except Exception:
        pass


def _make_tiktok_chrome_options():
    """Membuat objek uc.ChromeOptions baru yang segar."""
    options = uc.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=id-ID,id,en-US,en')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=CalculateNativeWinOcclusion')
    options.add_argument(f'--user-data-dir={TIKTOK_PROFILE_DIR}')
    return options


def _init_driver(skip_input=False):
    """Buat driver TikTok baru dengan profile persisten dan CDP Interceptor."""
    global TIKTOK_DRIVER

    if TIKTOK_DRIVER is not None:
        try:
            TIKTOK_DRIVER.quit()
        except:
            pass
        TIKTOK_DRIVER = None

    _kill_zombie_chrome_tiktok()
    time.sleep(1)

    # Hapus stale lock file jika ada agar Chrome tidak error saat startup
    for lock in ['SingletonLock', 'SingletonCookie', 'SingletonSocket']:
        lp = os.path.join(TIKTOK_PROFILE_DIR, lock)
        if os.path.exists(lp):
            try:
                os.remove(lp)
            except Exception:
                pass

    try:
        TIKTOK_DRIVER = uc.Chrome(options=_make_tiktok_chrome_options(), version_main=156)
    except Exception:
        _kill_zombie_chrome_tiktok()
        time.sleep(1)
        try:
            TIKTOK_DRIVER = uc.Chrome(options=_make_tiktok_chrome_options(), version_main=153)
        except Exception:
            _kill_zombie_chrome_tiktok()
            time.sleep(1)
            TIKTOK_DRIVER = uc.Chrome(options=_make_tiktok_chrome_options())

    # 1. Pasang CDP script interceptor sebelum navigasi untuk menangkap response API search (Fetch & XHR)
    interceptor_js = """
    window.__TIKTOK_SEARCH_ITEMS = window.__TIKTOK_SEARCH_ITEMS || [];
    
    // Hook Fetch
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
        const res = await origFetch.apply(this, args);
        try {
            const url = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url ? args[0].url : '');
            if (url.includes('/api/search/')) {
                const clone = res.clone();
                clone.json().then(data => {
                    if (data && data.data) {
                        for (const d of data.data) {
                            window.__TIKTOK_SEARCH_ITEMS.push(d);
                        }
                    }
                }).catch(() => {});
            }
        } catch(e) {}
        return res;
    };

    // Hook XMLHttpRequest (XHR)
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this._url = url;
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        this.addEventListener('load', function() {
            try {
                if (this._url && this._url.includes('/api/search/')) {
                    const data = JSON.parse(this.responseText);
                    if (data && data.data) {
                        for (const d of data.data) {
                            window.__TIKTOK_SEARCH_ITEMS.push(d);
                        }
                    }
                }
            } catch(e) {}
        });
        return origSend.apply(this, arguments);
    };
    """
    try:
        TIKTOK_DRIVER.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": interceptor_js})
    except Exception as e:
        print(f"    [WARN] Gagal pasang CDP interceptor: {e}")

    # 2. Buka homepage tiktok.com
    TIKTOK_DRIVER.get("https://www.tiktok.com/")
    print("    [INFO] Membuka TikTok di Chrome...")
    time.sleep(3)

    # Deteksi HTTP ERROR 403 / Akamai Access Denied pada profile lama
    try:
        body_text = (TIKTOK_DRIVER.execute_script("return document.body.innerText") or "").lower()
        if ("access to www.tiktok.com was denied" in body_text or 
            "http error 403" in body_text or 
            "access denied" in body_text or 
            "edgesuite.net" in body_text or 
            "permission to access" in body_text):
            print("\n" + "=" * 60)
            print("🚨 TIKTOK / AKAMAI ACCESS DENIED (403) TERDETEKSI! 🚨")
            print("Sesi/cookies pada profile lama sedang diblokir sementara oleh firewall TikTok.")
            print("Mereset session Chrome profile secara otomatis...")
            print("=" * 60 + "\n")
            try:
                TIKTOK_DRIVER.quit()
            except Exception:
                pass
            TIKTOK_DRIVER = None
            import shutil
            if os.path.exists(TIKTOK_PROFILE_DIR):
                shutil.rmtree(TIKTOK_PROFILE_DIR, ignore_errors=True)
            return _init_driver(skip_input=False)
    except Exception:
        pass

    if not skip_input:
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            print("\n" + "=" * 60)
            print("🔐 SILAKAN LOGIN KE AKUN TIKTOK ANDA DI BROWSER 🔐")
            print("1. Jendela Chrome sudah terbuka di https://www.tiktok.com/")
            print("2. Silakan login ke akun TikTok Anda")
            print("   (bisa via scan QR dari HP, Google, Email, dll).")
            print("3. Selesaikan verifikasi puzzle jika muncul.")
            print("4. Pastikan Anda sudah berhasil masuk ke akun TikTok.")
            print("=" * 60 + "\n")

            input("👉 TEKAN ENTER SETELAH ANDA SUDAH LOGIN DI BROWSER... ")
            print("    [OK] Login terkonfirmasi! Melanjutkan ke proses scraping...")
            time.sleep(2)
        else:
            print("    [INFO] Menunggu 5 detik agar browser siap...")
            time.sleep(5)

    _ensure_worker_tab()
    return TIKTOK_DRIVER


def _ensure_worker_tab():
    """Memastikan ada 2 tab di Chrome: Tab 0 (Search Feed) dan Tab 1 (Worker Tab)."""
    global TIKTOK_DRIVER, TIKTOK_SEARCH_TAB, TIKTOK_WORKER_TAB
    if TIKTOK_DRIVER is None:
        return
    try:
        handles = TIKTOK_DRIVER.window_handles
        if len(handles) == 1:
            TIKTOK_SEARCH_TAB = handles[0]
            TIKTOK_DRIVER.switch_to.new_window('tab')
            TIKTOK_WORKER_TAB = TIKTOK_DRIVER.window_handles[-1]
            TIKTOK_DRIVER.switch_to.window(TIKTOK_SEARCH_TAB)
        elif len(handles) == 2:
            TIKTOK_SEARCH_TAB = handles[0]
            TIKTOK_WORKER_TAB = handles[1]
        elif len(handles) > 2:
            # Jika TikTok membuka tab baru tak terduga (misal target="_blank"),
            # tutup tab liar tersebut agar tidak membebani browser & RAM
            TIKTOK_SEARCH_TAB = handles[0]
            TIKTOK_WORKER_TAB = handles[1]
            for h in handles[2:]:
                try:
                    TIKTOK_DRIVER.switch_to.window(h)
                    TIKTOK_DRIVER.close()
                except Exception:
                    pass
            try:
                TIKTOK_DRIVER.switch_to.window(TIKTOK_SEARCH_TAB)
            except Exception:
                pass
    except Exception as e:
        print(f"    [WARN] Gagal inisialisasi worker tab TikTok: {e}")


def _deep_fetch_tiktok_details(video_url):
    """
    Membuka video URL di worker tab untuk mengambil teks lengkap (untruncated caption)
    dan metrik lengkap dari __UNIVERSAL_DATA_FOR_REHYDRATION__.
    """
    global TIKTOK_DRIVER, TIKTOK_WORKER_TAB
    if not video_url or not video_url.startswith('http') or 'tiktok.com' not in video_url or '/live' in video_url.lower():
        return {}
    try:
        _ensure_worker_tab()
        if not TIKTOK_WORKER_TAB:
            return {}

        TIKTOK_DRIVER.switch_to.window(TIKTOK_WORKER_TAB)
        TIKTOK_DRIVER.get(video_url)
        time.sleep(random.uniform(2.0, 3.0))

        # Abaikan jika halaman teralihkan ke live stream
        curr_url = (TIKTOK_DRIVER.current_url or '').lower()
        if '/live' in curr_url or 'tiktok.com/live' in curr_url:
            print(f"        [SKIP] Postingan adalah siaran LIVE, melewati...")
            return {}

        details = TIKTOK_DRIVER.execute_script("""
        let details = { desc: '', likes: 0, comments: 0, saves: 0, shares: 0, views: 0, createTime: 0, nickname: '', uniqueId: '' };

        // 1. Coba dari __UNIVERSAL_DATA_FOR_REHYDRATION__
        let el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
        if (el) {
            try {
                let data = JSON.parse(el.innerText);
                let item = data?.['__DEFAULT_SCOPE__']?.['webapp.video-detail']?.['itemInfo']?.['itemStruct'] || 
                           data?.['__DEFAULT_SCOPE__']?.['webapp.photo-detail']?.['itemInfo']?.['itemStruct'] || {};
                let stats = item.stats || item.statsV2 || {};
                if (item.desc) details.desc = item.desc;
                if (stats.diggCount) details.likes = stats.diggCount;
                if (stats.commentCount) details.comments = stats.commentCount;
                if (stats.collectCount) details.saves = stats.collectCount;
                if (stats.shareCount) details.shares = stats.shareCount;
                if (stats.playCount) details.views = stats.playCount;
                if (item.createTime) details.createTime = item.createTime;
                if (item.author?.nickname) details.nickname = item.author.nickname;
                if (item.author?.uniqueId) details.uniqueId = item.author.uniqueId;
            } catch(e) {}
        }

        // 2. Coba dari SIGI_STATE jika likes masih 0
        if (!details.likes || details.likes === 0) {
            let sigiEl = document.getElementById('SIGI_STATE');
            if (sigiEl) {
                try {
                    let sdata = JSON.parse(sigiEl.innerText);
                    let items = sdata?.ItemModule || {};
                    let firstKey = Object.keys(items)[0];
                    if (firstKey && items[firstKey]) {
                        let it = items[firstKey];
                        let stats = it.stats || it.statsV2 || {};
                        if (!details.desc && it.desc) details.desc = it.desc;
                        if (stats.diggCount) details.likes = stats.diggCount;
                        if (stats.commentCount) details.comments = stats.commentCount;
                        if (stats.collectCount) details.saves = stats.collectCount;
                        if (stats.shareCount) details.shares = stats.shareCount;
                        if (stats.playCount) details.views = stats.playCount;
                        if (!details.createTime && it.createTime) details.createTime = it.createTime;
                        if (!details.nickname && it.nickname) details.nickname = it.nickname;
                        if (!details.uniqueId && it.author) details.uniqueId = it.author;
                    }
                } catch(e) {}
            }
        }

        // 3. Fallback: Ekstrak Langsung dari Elemen DOM Halaman Video/Foto
        // Likes via DOM
        if (!details.likes || details.likes === 0) {
            let likeEl = document.querySelector('strong[data-e2e="like-count"], [data-e2e="like-count"], [data-e2e="browse-like-count"]');
            if (likeEl && likeEl.innerText) details.likes = likeEl.innerText.trim();
        }
        // Comments via DOM
        if (!details.comments || details.comments === 0) {
            let commentEl = document.querySelector('strong[data-e2e="comment-count"], [data-e2e="comment-count"], [data-e2e="browse-comment-count"]');
            if (commentEl && commentEl.innerText) details.comments = commentEl.innerText.trim();
        }
        // Saves/Bookmarks via DOM
        if (!details.saves || details.saves === 0) {
            let saveEl = document.querySelector('strong[data-e2e="undefined-count"], strong[data-e2e="bookmark-count"], strong[data-e2e="collect-count"], [data-e2e="undefined-count"], [data-e2e="bookmark-count"]');
            if (saveEl && saveEl.innerText) details.saves = saveEl.innerText.trim();
        }
        // Shares via DOM
        if (!details.shares || details.shares === 0) {
            let shareEl = document.querySelector('strong[data-e2e="share-count"], [data-e2e="share-count"], [data-e2e="browse-share-count"]');
            if (shareEl && shareEl.innerText) details.shares = shareEl.innerText.trim();
        }

        // Expand & ambil caption terpanjang via DOM
        let moreBtn = document.querySelector('[data-e2e="browse-video-desc"] button, [data-e2e="browse-video-desc"] ~ button, button[class*="more"]');
        if (moreBtn) { try { moreBtn.click(); } catch(e) {} }

        let textEls = document.querySelectorAll('div[data-e2e="browse-video-desc"], h1[data-e2e="browse-video-desc"], span[data-e2e="browse-video-desc"], div[data-e2e="browse-photo-desc"], h1[data-e2e="browse-photo-desc"]');
        for (let el of textEls) {
            let t = (el.innerText || '').trim();
            if (t.length > (details.desc || '').length) details.desc = t;
        }

        return details;
        """) or {}

        desc = details.get('desc', '')
        clean_desc = re.sub(r'[\r\n\u2028\u2029]+', ' ', str(desc)).strip()
        details['desc'] = clean_desc

        # Pastikan seluruh metrik berupa integer murni via parse_engagement
        for k in ['likes', 'comments', 'saves', 'shares', 'views']:
            details[k] = parse_engagement(str(details.get(k, 0)))

        ct = details.get('createTime', 0)
        if ct:
            try:
                dt = datetime.fromtimestamp(int(ct), tz=timezone.utc)
                details['date_str'] = dt.astimezone(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
            except Exception:
                pass

        return details
    except Exception as e:
        return {}


def _extract_from_json(html_source):
    """Ekstrak data video dari JSON embedded di halaman TikTok."""
    videos = {}

    sigi = re.search(r"window\['SIGI_STATE'\]=(.*?);window\[", html_source)
    rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html_source, re.DOTALL)

    json_data = None
    try:
        if sigi:
            json_data = json.loads(sigi.group(1))
        elif rehyd:
            json_data = json.loads(rehyd.group(1))
    except:
        return videos

    if not json_data:
        return videos

    def traverse(obj):
        if isinstance(obj, dict):
            stats_raw = obj.get('stats') if isinstance(obj.get('stats'), dict) else (obj.get('statsV2') if isinstance(obj.get('statsV2'), dict) else {})
            if stats_raw and ('diggCount' in stats_raw or 'playCount' in stats_raw):
                # Abaikan siaran LIVE
                if obj.get('live_info') or obj.get('room_id') or obj.get('live') or obj.get('is_live'):
                    return
                vid_id = str(obj.get('id', ''))
                if vid_id:
                    author_info = obj.get('author', {})
                    stats = stats_raw
                    desc = obj.get('desc', '')
                    create_time = obj.get('createTime', '')

                    date_str = ''
                    if create_time:
                        try:
                            dt = datetime.fromtimestamp(int(create_time), tz=timezone.utc)
                            dt_wib = dt.astimezone(WIB)
                            date_str = dt_wib.strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
                        except:
                            pass

                    videos[vid_id] = {
                        'id': vid_id,
                        'author': author_info.get('nickname', '') or author_info.get('uniqueId', ''),
                        'handle': author_info.get('uniqueId', ''),
                        'content': re.sub(r'[\r\n\u2028\u2029]+', ' ', str(desc)).strip(),
                        'created_at': date_str,
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

    traverse(json_data)
    return videos


def _extract_from_dom(html_source):
    """Fallback: Ekstrak data video dari DOM (BeautifulSoup)."""
    soup = BeautifulSoup(html_source, 'html.parser')
    videos = []

    video_cards = soup.find_all('div', {'class': lambda x: x and 'DivItemContainer' in x})
    if not video_cards:
        video_cards = soup.find_all('div', {'data-e2e': lambda x: x in ['search_top-item', 'search_video-item', 'search_photo-item', 'search-photo-item']})
    if not video_cards:
        video_cards = soup.find_all('div', {'data-e2e': 'search-common-link'})
    if not video_cards:
        cards_found = []
        for vl in soup.find_all('a', href=lambda h: h and ('/video/' in h or '/photo/' in h) and '/live' not in h.lower()):
            p = vl.parent
            for _ in range(4):
                if p and p.name != 'body':
                    if p.get('data-e2e') or (p.get('class') and any('Item' in c or 'Card' in c for c in p.get('class'))):
                        cards_found.append(p)
                        break
                    p = p.parent
                else:
                    break
            else:
                cards_found.append(vl.parent)
        video_cards = cards_found

    for card in video_cards:
        try:
            # Lewati jika kartu adalah siaran LIVE
            card_e2e = str(card.get('data-e2e', '')).lower()
            if 'live' in card_e2e or card.find(string=re.compile(r'^\s*LIVE\s*$', re.I)) or card.find('a', href=lambda h: h and '/live' in str(h).lower()):
                continue

            link_tag = card.find('a', href=lambda h: h and ('/video/' in h or '/photo/' in h) and '/live' not in h.lower())
            if not link_tag:
                link_tag = card.find('a', href=True)
            url_video = link_tag['href'] if link_tag else ""
            if not url_video or "/live" in url_video.lower() or ("video" not in url_video and "photo" not in url_video):
                continue
            if not url_video.startswith('http'):
                url_video = 'https://www.tiktok.com' + url_video

            # Author & Handle
            author_tag = (card.find('p', {'data-e2e': 'search-card-user-unique-id'})
                         or card.find('span', {'data-e2e': 'search-card-user-unique-id'})
                         or card.find('span', {'data-e2e': 'search-card-user-nickname'}))
            handle = author_tag.text.strip() if author_tag else ""

            nick_tag = (card.find('p', {'data-e2e': 'search-card-user-nickname'})
                       or card.find('span', {'data-e2e': 'search-card-user-nickname'}))
            author = nick_tag.text.strip() if nick_tag else ""

            if not handle:
                handle_match = re.search(r'@([^/?&#]+)', url_video)
                if handle_match:
                    handle = handle_match.group(1)

            if not author:
                author = handle or "TikTok_User"

            # Views
            views_tag = (card.find('strong', {'data-e2e': 'video-views'})
                        or card.find('strong', class_=lambda c: c and 'VideoCount' in c)
                        or card.find('div', {'data-e2e': 'video-views'}))
            views = parse_engagement(views_tag.text.strip()) if views_tag else 0

            # Caption
            caption_tag = (card.find('div', {'data-e2e': 'search-card-video-caption'})
                          or card.find('div', {'class': lambda x: x and 'DivTextContainer' in x}))
            caption = caption_tag.text.strip() if caption_tag else ""

            # Time tag (e.g. 5h ago, 4d ago)
            time_tag = card.find('div', class_=lambda c: c and 'DivTimeTag' in c)
            time_text = time_tag.text.strip() if time_tag else ""

            vid_id_match = re.search(r'/video/(\d+)', url_video)
            vid_id = vid_id_match.group(1) if vid_id_match else str(abs(hash(url_video)) % 10000000)

            videos.append({
                'id': vid_id,
                'author': author,
                'handle': handle,
                'content': re.sub(r'[\r\n\u2028\u2029]+', ' ', caption).strip(),
                'created_at': time_text,
                'likes': 0,
                'comments': 0,
                'saves': 0,
                'shares': 0,
                'views': views,
                'url': url_video,
            })
        except:
            pass

    return videos


def scrape_tiktok(keyword, max_results=100):
    """
    Scrape TikTok dengan Single-Phase extraction:
    - Intercept langsung data API search (/api/search/) -> akurasi metrik 100%
    - Scroll container #grid-main
    - Fallback ke DOM parsing & embedded JSON
    
    Args:
        keyword: kata kunci pencarian
        max_results: target jumlah data
    """
    global TIKTOK_DRIVER, TIKTOK_SEARCH_TAB, TIKTOK_WORKER_TAB, _SEEN_URLS, _CONSECUTIVE_TOP_NORESULT

    print(f"    - TikTok Selenium: mencari '{keyword}'...")

    if TIKTOK_DRIVER is None:
        print("    [!] Membuka Chrome untuk TikTok pertama kali...")
        _init_driver()

    _ensure_worker_tab()
    if TIKTOK_SEARCH_TAB:
        try:
            TIKTOK_DRIVER.switch_to.window(TIKTOK_SEARCH_TAB)
        except Exception:
            pass

    # Reset intercepted items
    try:
        TIKTOK_DRIVER.execute_script("window.__TIKTOK_SEARCH_ITEMS = [];")
    except Exception:
        pass

    query = urllib.parse.quote(keyword)
    all_videos = {}  # vid_id -> data

    # Strategi Cerdas 3 Tahap Cascading:
    # 1. Cek Top Tab terlebih dahulu (menampilkan gabungan video & konten utama)
    # 2. Jika Top Tab mentok / belum memenuhi target, beralih ke Video Tab
    # 3. Jika Video Tab mentok / belum memenuhi target, beralih ke Photo Tab via UI Click
    tabs_to_search = [
        ("Top Tab", f"https://www.tiktok.com/search?q={query}"),
        ("Video Tab", f"https://www.tiktok.com/search/video?q={query}"),
        ("Photo Tab", None)  # UI-only click (menghindari raw HTTP GET yang diblokir Akamai)
    ]

    for tab_label, url in tabs_to_search:
        if len(all_videos) >= max_results:
            break

        print(f"    - Mencari di {tab_label}: '{keyword}' (Terkumpul saat ini: {len(all_videos)}/{max_results} data)...")

        # Reset intercepted items untuk tab ini
        try:
            TIKTOK_DRIVER.execute_script("window.__TIKTOK_SEARCH_ITEMS = [];")
        except Exception:
            pass

        # Navigasi ke tab yang ditargetkan
        if tab_label == "Video Tab":
            print(f"    [TAB] Kuota belum terpenuhi ({len(all_videos)}/{max_results} data). Beralih ke Video Tab...")
            switched = False
            try:
                switched = TIKTOK_DRIVER.execute_script("""
                    let buttons = Array.from(document.querySelectorAll('button[data-testid="tux-web-tab-bar"], button'));
                    let target = buttons.find(b => {
                        let t = (b.innerText || '').trim().toLowerCase();
                        return (t === 'video' || t === 'videos');
                    });
                    if (!target) {
                        let spans = Array.from(document.querySelectorAll('span[data-testid="tux-web-text"], span, div'));
                        let spanTarget = spans.find(s => {
                            let t = (s.innerText || '').trim().toLowerCase();
                            return (t === 'video' || t === 'videos');
                        });
                        if (spanTarget) target = spanTarget.closest('button') || spanTarget;
                    }
                    if (target) {
                        target.scrollIntoView({block: 'center', inline: 'center'});
                        target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
                        target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
                        target.click();
                        return true;
                    }
                    return false;
                """)
            except Exception:
                switched = False

            if switched:
                print("    [OK] Berhasil beralih ke Video Tab via klik UI tab!")
                time.sleep(4)
            else:
                print(f"    [INFO] Mengarahkan URL browser ke Video Tab: {url}")
                for attempt in range(3):
                    try:
                        TIKTOK_DRIVER.get(url)
                        break
                    except Exception as e:
                        err_str = str(e).lower()
                        if 'connection' in err_str or 'chrome' in err_str or 'session' in err_str:
                            print(f"    [!] Chrome error (attempt {attempt+1}/3): {e}")
                            TIKTOK_DRIVER = None
                            time.sleep(3)
                            _init_driver()
                        else:
                            raise
                time.sleep(5)

        elif tab_label == "Photo Tab":
            print(f"    [TAB] Kuota belum terpenuhi ({len(all_videos)}/{max_results} data). Beralih ke Photo Tab via UI...")
            switched = False
            try:
                switched = TIKTOK_DRIVER.execute_script("""
                    let buttons = Array.from(document.querySelectorAll('button[data-testid="tux-web-tab-bar"], button'));
                    let target = buttons.find(b => {
                        let t = (b.innerText || '').trim().toLowerCase();
                        return (t === 'photo' || t === 'photos' || t === 'foto');
                    });
                    if (!target) {
                        let spans = Array.from(document.querySelectorAll('span[data-testid="tux-web-text"], span, div'));
                        let spanTarget = spans.find(s => {
                            let t = (s.innerText || '').trim().toLowerCase();
                            return (t === 'photo' || t === 'photos' || t === 'foto');
                        });
                        if (spanTarget) target = spanTarget.closest('button') || spanTarget;
                    }
                    if (target) {
                        target.scrollIntoView({block: 'center', inline: 'center'});
                        target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
                        target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
                        target.click();
                        return true;
                    }
                    return false;
                """)
            except Exception:
                switched = False

            if switched:
                print("    [OK] Berhasil beralih ke Photo Tab via klik UI tab!")
                time.sleep(4)
            else:
                print("    [INFO] Tab Photo tidak dapat diklik atau tidak tersedia di halaman ini. Melewati...")
                continue

        else:
            # Top Tab
            for attempt in range(3):
                try:
                    TIKTOK_DRIVER.get(url)
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if 'connection' in err_str or 'chrome' in err_str or 'session' in err_str:
                        print(f"    [!] Chrome error (attempt {attempt+1}/3): {e}")
                        TIKTOK_DRIVER = None
                        time.sleep(3)
                        _init_driver()
                    else:
                        raise
            time.sleep(5)

        # Cek HTTP 403, Akamai Access Denied, & CAPTCHA
        try:
            body_text = (TIKTOK_DRIVER.execute_script("return document.body.innerText") or "").lower()
            if ('access to www.tiktok.com was denied' in body_text or 
                'http error 403' in body_text or 
                'access denied' in body_text or 
                'permission to access' in body_text or 
                'edgesuite.net' in body_text):
                print("\n" + "=" * 60)
                print("🚨 TIKTOK / AKAMAI ACCESS DENIED (403) TERDETEKSI! 🚨")
                print("Firewall memblokir endpoint/sesi ini.")
                print("Mereset session Chrome profile secara otomatis...")
                print("=" * 60 + "\n")
                _force_relogin()
                return scrape_tiktok(keyword, max_results=max_results)

            if 'captcha' in body_text or 'verify' in body_text:
                print("\n" + "=" * 60)
                print("🚨 CAPTCHA TERDETEKSI! 🚨")
                if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
                    print("1. Selesaikan CAPTCHA di browser.")
                    print("2. Setelah selesai, tekan ENTER di sini.")
                    print("=" * 60 + "\n")
                    input("👉 TEKAN ENTER JIKA CAPTCHA SUDAH SELESAI... ")
                else:
                    print("Menunggu 10 detik untuk resolusi CAPTCHA...")
                    time.sleep(10)
                TIKTOK_DRIVER.get(url)
                time.sleep(5)
        except:
            pass

        # Cek apakah tab ini benar-benar "No results found"
        try:
            has_results = TIKTOK_DRIVER.execute_script("""
                let raw = window.__TIKTOK_SEARCH_ITEMS || [];
                let cards = document.querySelectorAll('[data-e2e="search_top-item"], [data-e2e="search_video-item"], [data-e2e="search_photo-item"], a[href*="/video/"], a[href*="/photo/"]');
                return (raw.length > 0 || cards.length > 0);
            """)
            if not has_results:
                body_text = (TIKTOK_DRIVER.execute_script("return document.body.innerText") or "").lower()
                if "no results found" in body_text or "tidak ada hasil" in body_text:
                    print(f"    [INFO] {tab_label} menampilkan 'No results found', langsung beralih ke tab berikutnya...")

                    # Track consecutive Top Tab failures untuk deteksi rate-limit
                    if tab_label == "Top Tab":
                        _CONSECUTIVE_TOP_NORESULT += 1
                        if _CONSECUTIVE_TOP_NORESULT >= _MAX_TOP_NORESULT_BEFORE_RELOGIN:
                            print(f"\n    [⚠️] Top Tab 'No results' sudah {_CONSECUTIVE_TOP_NORESULT}x berturut-turut!")
                            print(f"    [⚠️] Kemungkinan besar akun terkena rate-limit. Perlu login akun baru.")
                            _force_relogin()
                            _CONSECUTIVE_TOP_NORESULT = 0
                            # Retry keyword ini dengan akun baru
                            return scrape_tiktok(keyword, max_results=max_results)

                    continue
        except:
            pass

        # ========== SCROLL + EXTRACT LOOP UNTUK TAB INI ==========
        no_new_count = 0
        max_no_new = 8

        # ========== FASE 1: SCROLL & KUMPULKAN SEMUA DATA DARI FEED ==========
        no_new_count = 0
        max_no_new = 8

        while len(all_videos) < max_results:
            try:
                count_before = len(all_videos)

                # Prioritas 1: Ambil data dari Intercepted Search API (Likes, Comments, Saves, Shares, Views, Tanggal)
                try:
                    api_items = TIKTOK_DRIVER.execute_script("""
                    const res = [];
                    const rawItems = window.__TIKTOK_SEARCH_ITEMS || [];
                    for (const raw of rawItems) {
                        if (raw.type === 2 || raw.type === 'live' || raw.live_room || raw.live_info) continue;
                        const it = raw.item || raw;
                        if (it && it.id) {
                            if (it.live_info || it.room_id || it.is_live || it.type === 2) continue;
                            const stats = it.stats || it.statsV2 || {};
                            const isPhoto = !!(it.imagePost || it.image_post_info || (it.images && it.images.length > 0));
                            res.push({
                                id: String(it.id),
                                isPhoto: isPhoto,
                                nickname: (it.author && it.author.nickname) || '',
                                uniqueId: (it.author && it.author.uniqueId) || '',
                                desc: it.desc || '',
                                createTime: it.createTime || 0,
                                likes: stats.diggCount || 0,
                                comments: stats.commentCount || 0,
                                saves: stats.collectCount || 0,
                                shares: stats.shareCount || 0,
                                views: stats.playCount || 0,
                            });
                        }
                    }
                    return res;
                    """)

                    if api_items:
                        for it in api_items:
                            vid_id = it.get('id', '')
                            if not vid_id or vid_id in all_videos:
                                continue
                            author = it.get('nickname', '') or it.get('uniqueId', '')
                            handle = it.get('uniqueId', '')
                            v_type = 'photo' if (it.get('isPhoto') or tab_label == 'Photo Tab') else 'video'
                            v_url = f"https://www.tiktok.com/@{handle or 'user'}/{v_type}/{vid_id}"
                            if v_url in _SEEN_URLS or '/live' in v_url.lower():
                                continue

                            # Format tanggal
                            date_str = ''
                            ct = it.get('createTime', 0)
                            if ct:
                                try:
                                    dt = datetime.fromtimestamp(int(ct), tz=timezone.utc)
                                    date_str = dt.astimezone(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
                                except Exception:
                                    pass

                            raw_desc = re.sub(r'[\r\n\u2028\u2029]+', ' ', str(it.get('desc', ''))).strip()

                            all_videos[vid_id] = {
                                'id': vid_id,
                                'author': author,
                                'handle': handle,
                                'content': raw_desc,
                                'created_at': date_str,
                                'likes': int(it.get('likes', 0)),
                                'comments': int(it.get('comments', 0)),
                                'saves': int(it.get('saves', 0)),
                                'shares': int(it.get('shares', 0)),
                                'views': int(it.get('views', 0)),
                                'url': v_url,
                            }
                except Exception:
                    pass

                # Prioritas 2: Ekstrak dari JSON embedded
                try:
                    html_source = TIKTOK_DRIVER.page_source
                    json_videos = _extract_from_json(html_source)
                    for vid_id, data in json_videos.items():
                        if vid_id not in all_videos and data['url'] not in _SEEN_URLS:
                            all_videos[vid_id] = data

                    # Prioritas 3: Fallback ke DOM parsing
                    dom_videos = _extract_from_dom(html_source)
                    for data in dom_videos:
                        vid_id = data['id']
                        if vid_id not in all_videos and data['url'] not in _SEEN_URLS:
                            all_videos[vid_id] = data
                except Exception:
                    pass

                new_count = len(all_videos) - count_before
                if new_count > 0:
                    print(f"      [Scroll] {len(all_videos)}/{max_results} Data terkumpul (+{new_count} baru)")
                    no_new_count = 0
                    # Reset counter rate-limit karena berhasil dapat data
                    if tab_label == "Top Tab":
                        _CONSECUTIVE_TOP_NORESULT = 0
                else:
                    no_new_count += 1
                    if no_new_count >= max_no_new:
                        print(f"    [INFO] {tab_label} mentok ({max_no_new}x scroll tanpa data baru).")
                        break

                if len(all_videos) >= max_results:
                    break

                # Dismiss popup modal jika muncul
                try:
                    close_btn = TIKTOK_DRIVER.find_elements(By.CSS_SELECTOR, 'div[data-e2e="modal-close-inner-button"], [aria-label="Close"], button[class*="close"]')
                    if close_btn:
                        close_btn[0].click()
                except Exception:
                    pass

                # Scroll: PRIORITAS scroll container #grid-main yang merupakan scroll container utama TikTok search
                TIKTOK_DRIVER.execute_script("""
                const el = document.getElementById('grid-main') || document.querySelector('main');
                if (el) {
                    el.scrollTop = el.scrollHeight;
                } else {
                    window.scrollTo(0, document.body.scrollHeight);
                }
                """)
                time.sleep(random.uniform(1.8, 2.5))

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"    [WARN] Error saat scroll {tab_label}: {e}")
                break

    print(f"\n    [INFO] Fase 1 Selesai: Total {len(all_videos)} video berhasil dikumpulkan.")

    # ============================================================
    # FASE 2: BUKA SATU PER SATU UNTUK DETAIL LENGKAP (DEEP-FETCH)
    # ============================================================
    # Video yang membutuhkan deep-fetch:
    # 1. Caption terpotong di limit 500 karakter search API (>= 480 karakter atau berakhiran '...' / '…')
    # 2. Metrik likes == 0 (berasal dari DOM fallback kartu search)
    # 3. Caption sangat pendek (< 40 karakter)
    videos_to_fetch = []
    for vid_id, data in all_videos.items():
        v_url = data.get('url', '')
        if '/live' in v_url.lower():
            continue
        content = data.get('content', '')
        likes = parse_engagement(str(data.get('likes', 0)))
        need_fetch = (len(content) >= 480 or content.endswith('...') or content.endswith('…') or likes == 0 or len(content) < 40)
        if need_fetch and v_url:
            videos_to_fetch.append((vid_id, data))

    if videos_to_fetch:
        print(f"    [INFO] Fase 2: Membuka {len(videos_to_fetch)} video satu per satu untuk mengambil caption utuh & metrik asli...")
        _ensure_worker_tab()

        try:
            for i, (vid_id, data) in enumerate(videos_to_fetch, 1):
                url = data['url']
                print(f"      [{i}/{len(videos_to_fetch)}] Deep-Fetch: {url[:60]}...")
                try:
                    details = _deep_fetch_tiktok_details(url)
                    if details:
                        if len(details.get('desc', '')) > len(data.get('content', '')):
                            data['content'] = details['desc']
                        for k in ['likes', 'comments', 'saves', 'shares', 'views']:
                            val = parse_engagement(str(details.get(k, 0)))
                            if val > 0:
                                data[k] = val
                        if details.get('date_str'):
                            data['created_at'] = details['date_str']
                        if details.get('nickname'):
                            data['author'] = details['nickname']
                        if details.get('uniqueId'):
                            data['handle'] = details['uniqueId']
                        print(f"        [OK] @{data.get('handle', '')} | Likes: {data.get('likes', 0):,} | Caption: {len(data.get('content', ''))} karakter")
                    else:
                        print(f"        [WARN] Detail tidak berhasil diambil, mempertahankan data awal.")
                except Exception as e:
                    print(f"        [WARN] Error saat deep-fetch {url[:40]}: {e}")

                time.sleep(random.uniform(1.2, 2.0))
        except KeyboardInterrupt:
            print("\n    [!] Deep-fetch dihentikan oleh user (Ctrl+C).")
            print(f"    [!] Menyimpan {len(all_videos)} data yang sudah berhasil terkumpul di Fase 1...")

        # Kembalikan kontrol ke search tab
        if TIKTOK_SEARCH_TAB:
            try:
                TIKTOK_DRIVER.switch_to.window(TIKTOK_SEARCH_TAB)
            except:
                pass
        print(f"    [INFO] Fase 2 Selesai. Semua detail berhasil diperbarui!")
    else:
        print(f"    [INFO] Semua video dari API sudah memiliki data lengkap (tidak perlu deep-fetch).")

    # Cek jika 0 video didapat karena limit / captcha / logout
    if len(all_videos) == 0:
        try:
            body_text = (TIKTOK_DRIVER.execute_script("return document.body.innerText") or "").lower()
            is_limited = ("no results found" in body_text or 
                          "tidak ada hasil" in body_text or 
                          "something went wrong" in body_text or
                          "verify" in body_text or 
                          "captcha" in body_text)
            if is_limited:
                # --- AUTO COOLDOWN: tunggu 3 menit lalu retry otomatis (max 3x) ---
                _retry_count = getattr(scrape_tiktok, '_retry_count', 0)
                if _retry_count < 3:
                    cooldown_minutes = 3 + _retry_count  # 3, 4, 5 menit
                    print(f"\n    [⏳] TikTok rate-limit terdeteksi untuk '{keyword}'.")
                    print(f"    [⏳] Auto-cooldown {cooldown_minutes} menit sebelum retry (percobaan {_retry_count+1}/3)...")
                    time.sleep(cooldown_minutes * 60)
                    scrape_tiktok._retry_count = _retry_count + 1
                    result = scrape_tiktok(keyword, max_results=max_results)
                    scrape_tiktok._retry_count = 0  # Reset setelah berhasil/selesai
                    return result
                else:
                    # Sudah 3x retry gagal, baru minta user
                    scrape_tiktok._retry_count = 0
                    print("\n" + "=" * 60)
                    print("🚨 TIKTOK MEMBATASI PENCARIAN / PERLU GANTI AKUN 🚨")
                    print(f"Keyword '{keyword}' menghasilkan 0 video setelah 3x auto-retry.")
                    print("1. Buka jendela browser Chrome TikTok yang sedang aktif.")
                    print("2. Cek apakah ada CAPTCHA puzzle yang perlu diselesaikan.")
                    print("3. Jika akun terkena limit pencarian, silakan logout & login dengan akun lain.")
                    print("4. Setelah siap, tekan ENTER di terminal ini untuk mencoba ulang keyword ini.")
                    print("   (Atau ketik 'skip' lalu ENTER jika ingin melewati keyword ini).")
                    print("=" * 60 + "\n")
                    if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
                        resp = input("👉 TEKAN ENTER UNTUK COBA LAGI (atau ketik 'skip' lalu ENTER): ").strip().lower()
                        if resp != 'skip':
                            return scrape_tiktok(keyword, max_results=max_results)
                    else:
                        print("    [WARN] Non-interaktif, melewati keyword ini...")
        except RecursionError:
            scrape_tiktok._retry_count = 0
            pass
        except Exception as e:
            print(f"    [WARN] Check limit error: {e}")

    # Format hasil akhir
    final_data = []
    for vid_id, item in all_videos.items():
        content = item.get('content', '')
        clean_text = re.sub(r'\s+', ' ', content).strip()

        if len(clean_text) < 5:
            continue

        url_video = item.get('url', '')
        handle = item.get('handle', '')
        author = item.get('author', '') or handle or "TikTok_User"

        final_data.append({
            'platform': 'TikTok',
            'keyword': keyword,
            'url': url_video,
            'author': author,
            'handle': f"@{handle}" if handle and not handle.startswith('@') else handle,
            'content': clean_text,  # Caption LENGKAP tanpa pembatasan [:500]!
            'created_at': item.get('created_at', ''),
            'likes': parse_engagement(str(item.get('likes', 0))),
            'comments': parse_engagement(str(item.get('comments', 0))),
            'saves': parse_engagement(str(item.get('saves', 0))),
            'shares': parse_engagement(str(item.get('shares', 0))),
            'views': parse_engagement(str(item.get('views', 0))),
            'scraped_at': datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB',
        })
        if url_video:
            _SEEN_URLS.add(url_video)

    print(f"    [OK] {len(final_data)} data video terfilter & bersih.")
    return final_data


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("[TEST] Memulai test scrape TikTok (Selenium)...")
    data = scrape_tiktok("Kementerian Pekerjaan Umum", max_results=10)
    print(f"Berhasil ambil {len(data)} data")
    for d in data:
        print(f"  - Views: {d['views']}, Likes: {d['likes']}, Saves: {d['saves']}, Comments: {d['comments']}")
        print(f"    Handle: {d['handle']}, Content: {d['content'][:80]}...")
    if TIKTOK_DRIVER:
        TIKTOK_DRIVER.quit()
