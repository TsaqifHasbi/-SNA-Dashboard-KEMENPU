# ============================================================
# CELL 4: SCRAPING TWITTER/X (SELENIUM UNDETECTED)
# - 2 Fase: Kumpulkan URL → Ekstraksi di Tab Baru
# - Filter tanggal: 1 Januari 2025 - sekarang
# - Deduplikasi URL global
# - Auto-resume support
# - Tanpa batasan max_results (full crawl)
# ============================================================
import time
import urllib.parse
import os
import subprocess
import random
from datetime import datetime, timezone, timedelta

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

try:
    from cell_02_config import TWITTER_COOKIES, detect_topic
except ImportError:
    TWITTER_COOKIES = {}
    detect_topic = None

# Simpan driver di level global agar login hanya 1x sepanjang program jalan
TWITTER_DRIVER = None

# Path untuk Chrome profile persisten (login disimpan)
TW_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".tw_scraper_profile")

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

# Tanggal cutoff: 1 Januari 2025
DATE_CUTOFF = datetime(2025, 1, 1, tzinfo=timezone.utc)

# ---- Global tracking ----
_SEEN_URLS = set()  # URL tweet yang sudah pernah di-scrape


def reset_tracking():
    """Reset tracking (untuk awal run baru tanpa resume)."""
    global _SEEN_URLS
    _SEEN_URLS = set()


def load_seen_urls(urls):
    """Load URL yang sudah ada dari CSV sebelumnya (untuk resume)."""
    global _SEEN_URLS
    _SEEN_URLS.update(urls)
    print(f"    [DEDUP] {len(_SEEN_URLS)} URL sudah diketahui, akan di-skip.")


# ---- Helpers ----

def _to_wib(date_str):
    """Convert ISO datetime string ke format WIB."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        dt_wib = dt.astimezone(WIB)
        return dt_wib.strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
    except Exception:
        return date_str


def _is_after_cutoff(date_str):
    """Cek apakah tanggal tweet >= 1 Januari 2025."""
    if not date_str:
        return True  # Jika tidak ada tanggal, tetap ambil
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt >= DATE_CUTOFF
    except Exception:
        return True


def _get_chrome_major_version():
    """Deteksi versi major Chrome dari Windows Registry secara dinamis."""
    try:
        import winreg
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                key = winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon")
                v, _ = winreg.QueryValueEx(key, "version")
                if v and '.' in v:
                    return int(v.split('.')[0])
            except Exception:
                pass
    except Exception:
        pass
    return None


def _build_chrome_options():
    options = uc.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=id-ID,id,en-US,en')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=Translate,CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,ThrottleDisplayNoneAndDisplayInlineCSS')
    options.add_argument(f'--user-data-dir={TW_PROFILE_DIR}')

    prefs = {
        "intl.accept_languages": "id-ID,id,en-US,en",
        "translate": {"enabled": False}
    }
    options.add_experimental_option("prefs", prefs)
    return options


def _is_twitter_authenticated():
    """Cek apakah sesi login Twitter/X benar-benar aktif di browser."""
    global TWITTER_DRIVER
    if TWITTER_DRIVER is None:
        return False
    try:
        cur_url = (TWITTER_DRIVER.current_url or "").lower()
        if any(x in cur_url for x in ["login", "i/flow", "signup"]):
            return False

        is_auth = TWITTER_DRIVER.execute_script("""
            return !!(
                document.querySelector('[data-testid="AppTabBar_Home_Link"]') ||
                document.querySelector('[data-testid="SideNav_AccountSwitcher_Button"]') ||
                document.querySelector('a[href="/home"]') ||
                document.querySelector('nav[aria-label="Primary"]') ||
                document.querySelector('nav[aria-label="Navigasi Utama"]')
            );
        """)
        return bool(is_auth)
    except Exception:
        return False


def _init_driver():
    """Buat driver baru dengan profile persisten."""
    global TWITTER_DRIVER

    # Tutup driver lama jika ada
    if TWITTER_DRIVER is not None:
        try:
            TWITTER_DRIVER.quit()
        except:
            pass
        TWITTER_DRIVER = None

    # Kill hanya proses chrome milik Twitter (.tw_scraper_profile) agar aman dijalankan bersamaan
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            if p.info['name'] and 'chrome' in p.info['name'].lower():
                cmd = ' '.join(p.info['cmdline'] or [])
                if '.tw_scraper_profile' in cmd:
                    p.kill()
    except Exception:
        pass



    # Fix infinite hang when downloading chromedriver
    import socket
    socket.setdefaulttimeout(30)

    major_v = _get_chrome_major_version()
    driver_started = False

    if major_v:
        try:
            TWITTER_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=major_v)
            driver_started = True
        except Exception:
            time.sleep(1)

    if not driver_started:
        try:
            TWITTER_DRIVER = uc.Chrome(options=_build_chrome_options())
            driver_started = True
        except Exception:
            time.sleep(1)

    if not driver_started and major_v:
        for fallback_v in [major_v - 1, major_v - 2]:
            try:
                TWITTER_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=fallback_v)
                driver_started = True
                break
            except Exception:
                pass

    if not driver_started or TWITTER_DRIVER is None:
        raise RuntimeError("Gagal membuka Chrome Selenium untuk Twitter/X.")

    # Cek apakah sudah login
    TWITTER_DRIVER.get("https://x.com/home")
    print("    [INFO] Menunggu beranda Twitter dimuat...")
    time.sleep(4)

    # Injeksi cookie auth_token jika tersedia
    if TWITTER_COOKIES and isinstance(TWITTER_COOKIES, dict):
        try:
            cookies = TWITTER_DRIVER.get_cookies()
            has_auth = any(c.get('name') == 'auth_token' for c in cookies)
            if not has_auth and 'auth_token' in TWITTER_COOKIES:
                print("    [INFO] Menginjeksikan auth_token cookie dari konfigurasi...")
                TWITTER_DRIVER.add_cookie({'name': 'auth_token', 'value': TWITTER_COOKIES['auth_token'], 'domain': '.x.com', 'path': '/'})
                if 'ct0' in TWITTER_COOKIES:
                    TWITTER_DRIVER.add_cookie({'name': 'ct0', 'value': TWITTER_COOKIES['ct0'], 'domain': '.x.com', 'path': '/'})
                TWITTER_DRIVER.get("https://x.com/home")
                time.sleep(4)
        except Exception as e_cook:
            print(f"    [WARN] Injeksi cookie Twitter gagal: {e_cook}")

    time.sleep(3)
    is_auth = _is_twitter_authenticated()

    if is_auth:
        print("    [OK] Sesi login Twitter terverifikasi aktif!")
    else:
        print("\n" + "=" * 60)
        print("🚨 WAJIB LOGIN TWITTER (X) DI CHROME 🚨")
        print("1. Jendela Chrome saat ini terbuka di layar Anda.")
        print("2. Silakan LOGIN secara manual ke akun Twitter Anda di Chrome tersebut.")
        print("3. Pastikan beranda/feed Twitter (x.com/home) sudah terbuka normal.")
        print("4. Jika diminta verifikasi Email / Captcha, selesaikan di browser.")
        print("=" * 60 + "\n")
        input("👉 TEKAN ENTER DI TERMINAL INI SETELAH ANDA SELESAI LOGIN & BERANDA MUNCUL... ")
        print("    [OK] Melanjutkan ke pencarian...")
        time.sleep(2)

    return TWITTER_DRIVER


def scrape_twitter(keyword, max_results=500):
    """
    Scrape Twitter/X dengan 2 fase:
    - Fase 1: Scroll halaman search untuk kumpulkan URL tweet
    - Fase 2: Buka setiap URL di tab baru untuk ekstraksi data detail
    
    Filter: hanya tweet dari 1 Januari 2025 - sekarang.
    """
    global TWITTER_DRIVER, _SEEN_URLS

    print(f"    - Twitter Selenium: mencari '{keyword}'...")

    if TWITTER_DRIVER is None:
        print("    [!] Membuka Chrome untuk Twitter pertama kali...")
        _init_driver()

    # ========== FASE 1: KUMPULKAN URL DARI SEARCH ==========
    print(f"    [FASE 1] Mengumpulkan URL tweet dari pencarian...")

    # Gunakan query biasa tanpa filter since atau lang, karena kita fokus ke Top engagement murni
    query_text = keyword
    query = urllib.parse.quote(query_text)
    
    # Mulai dari tab 'Top' (Teratas / Populer) untuk menangkap tweet viral & tokoh sentral
    url = f"https://x.com/search?q={query}&src=typed_query"

    TWITTER_DRIVER.get(url)

    # Tunggu tweet pertama muncul atau handle error
    try:
        WebDriverWait(TWITTER_DRIVER, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
        )
    except Exception:
        # Cek apakah terkena error "Something went wrong" atau "No results"
        try:
            body_text = (TWITTER_DRIVER.execute_script("return document.body.innerText") or "").lower()
            
            if "no results for" in body_text or "tidak ada hasil untuk" in body_text:
                print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                return []
                
            error_keywords = ["something went wrong", "ada yang salah", "try reloading", "kesalahan teknis", "muat ulang", "rate limit", "batas frekuensi", "batas terlampaui", "cannot retrieve", "tidak dapat memuat"]
            if any(err in body_text for err in error_keywords):
                print("\n    [!] ERROR: Twitter memblokir pencarian atau terkena rate limit.")
                if "rate limit" in body_text or "batas" in body_text:
                    print("    [WARN] Akun Anda sedang terkena Rate Limit pencarian dari Twitter.")
                    print("    [INFO] Anda bisa menunggu beberapa menit atau mengganti akun Twitter di jendela Chrome.")
                else:
                    print("    [INFO] Cek jendela Chrome Anda: pastikan akun masih login dan pencarian berhasil memuat tweet.")
                
                print("\n" + "=" * 60)
                print("🚨 CEK BROWSER TWITTER (X) 🚨")
                print("1. Periksa jendela Chrome yang terbuka.")
                print("2. Jika perlu login ulang / ganti akun, silakan lakukan langsung di Chrome tersebut.")
                print("3. Pastikan tweet pencarian sudah muncul di layar browser.")
                print("4. Setelah tweet muncul normal di browser, kembali ke terminal lalu tekan ENTER.")
                print("=" * 60 + "\n")
                
                input("👉 TEKAN ENTER SETELAH BROWSER NORMAL & TWEET MUNCUL... ")
                
                print("    [INFO] Melanjutkan pencarian...")
                TWITTER_DRIVER.get(url)
                try:
                    WebDriverWait(TWITTER_DRIVER, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
                    )
                except Exception:
                    pass
        except Exception:
            pass

    time.sleep(3)
    
    # Cek jumlah tweet di layar untuk debug
    try:
        article_count = TWITTER_DRIVER.execute_script('return document.querySelectorAll(\'article[data-testid="tweet"]\').length')
        print(f"    [DEBUG] Jumlah tweet di layar awal: {article_count}")
        
        # Jika masih 0, cek dulu apakah benar-benar kosong
        if article_count == 0:
            body_text = (TWITTER_DRIVER.execute_script("return document.body.innerText") or "").lower()
            if "no results for" in body_text or "tidak ada hasil untuk" in body_text:
                print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                return []
                
            print("    [!] Masih 0 tweet. Coba refresh paksa...")
            TWITTER_DRIVER.refresh()
            time.sleep(7)
            article_count = TWITTER_DRIVER.execute_script('return document.querySelectorAll(\'article[data-testid="tweet"]\').length')
            print(f"    [DEBUG] Jumlah tweet setelah refresh paksa: {article_count}")

            # Jika masih 0, coba cari tombol Retry
            if article_count == 0:
                clicked_retry = TWITTER_DRIVER.execute_script("""
                    let btns = document.querySelectorAll('button');
                    for (let btn of btns) {
                        let txt = (btn.innerText || '').toLowerCase();
                        if (txt.includes('retry') || txt.includes('coba lagi')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                """)
                if clicked_retry:
                    print("    [INFO] Menekan tombol 'Retry / Coba lagi' di layar awal...")
                    time.sleep(6)
                    article_count = TWITTER_DRIVER.execute_script('return document.querySelectorAll(\'article[data-testid="tweet"]\').length')
                    print(f"    [DEBUG] Jumlah tweet setelah Retry: {article_count}")

            # Jika setelah refresh & retry masih 0 tweet dan bukan karena 'no results':
            if article_count == 0:
                body_text = (TWITTER_DRIVER.execute_script("return document.body.innerText") or "").lower()
                if "no results for" in body_text or "tidak ada hasil untuk" in body_text:
                    print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                    return []
                
                print("\n" + "=" * 60)
                print("🚨 TWITTER TIDAK MENAMPILKAN TWEET (RATE LIMIT / SESI MACET) 🚨")
                print(f"Keyword: '{keyword}' tidak memuat data di layar browser.")
                print("1. Cek jendela Chrome: apakah halaman blank, terkena limit pencarian, atau perlu re-login.")
                print("2. Jika akun terkena limit, Anda bisa ganti/login akun lain di browser Chrome tersebut.")
                print("3. Pastikan pencarian manual di Chrome berhasil memunculkan tweet.")
                print("4. Setelah aman, kembali ke sini dan tekan ENTER untuk mencoba lagi.")
                print("=" * 60 + "\n")
                input("👉 TEKAN ENTER JIKA SUDAH AMAN / SIAP COBA LAGI... ")
                TWITTER_DRIVER.get(url)
                time.sleep(5)
                article_count = TWITTER_DRIVER.execute_script('return document.querySelectorAll(\'article[data-testid="tweet"]\').length')
                print(f"    [DEBUG] Jumlah tweet setelah re-login/refresh: {article_count}")
    except:
        pass

    # Kumpulkan Data tweet dari halaman search secara LANGSUNG (Single-Phase)
    all_tweet_data = {} # dictionary url -> data
    last_height = TWITTER_DRIVER.execute_script("return document.body.scrollHeight")
    no_new_count = 0
    max_no_new = 8
    
    collect_data_js = r"""
    const results = [];
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    for (const article of articles) {
        try {
            let tweetUrl = '';
            const links = article.querySelectorAll('a[href*="/status/"]');
            for (const link of links) {
                if (link.href.includes('/status/') && !link.href.includes('/photo/') && !link.href.includes('/video/') && !link.href.includes('/analytics')) {
                    tweetUrl = link.href.split('?')[0];
                    break;
                }
            }
            if (!tweetUrl) continue;

            let dateStr = '';
            const timeEl = article.querySelector('time');
            if (timeEl) dateStr = timeEl.getAttribute('datetime') || '';

            let text = '';
            // Auto-expand 'Show more' / 'Tampilkan lebih banyak' jika ada tweet panjang (X Premium)
            const showMoreBtn = article.querySelector('[data-testid="tweet-text-show-more-link"]');
            if (showMoreBtn) {
                try { showMoreBtn.click(); } catch(e) {}
            }
            const textDiv = article.querySelector('div[data-testid="tweetText"]');
            if (textDiv) text = textDiv.innerText;

            let handle = '';
            const userLinks = article.querySelectorAll('a[role="link"]');
            for (const ul of userLinks) {
                const textContent = ul.innerText;
                if (textContent.includes('@')) {
                    const match = textContent.match(/@[\w_]+/);
                    if (match) {
                        handle = match[0];
                        break;
                    }
                }
            }

            let likes=0, views=0, retweets=0, replies=0;
            const groups = article.querySelectorAll('[role="group"]');
            if (groups.length > 0) {
                const btns = groups[0].querySelectorAll('[role="button"], a');
                for (const btn of btns) {
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    const testId = (btn.getAttribute('data-testid') || '').toLowerCase();
                    let valStr = btn.innerText.trim();
                    
                    let val = 0;
                    if (valStr) {
                        valStr = valStr.replace(/,/g, '');
                        if (valStr.match(/K/i)) val = parseFloat(valStr) * 1000;
                        else if (valStr.match(/M/i)) val = parseFloat(valStr) * 1000000;
                        else val = parseInt(valStr) || 0;
                    }

                    if (testId === 'reply' || aria.includes('balas') || aria.includes('reply')) replies = val;
                    else if (testId === 'retweet' || aria.includes('repost') || aria.includes('retweet')) retweets = val;
                    else if (testId === 'like' || aria.includes('suka') || aria.includes('like')) likes = val;
                    else if (aria.includes('tayangan') || aria.includes('view') || testId.includes('view')) views = val;
                }
            }

            results.push({
                url: tweetUrl,
                date: dateStr,
                text: text,
                username: handle,
                likes: likes,
                views: views,
                retweets: retweets,
                replies: replies
            });
        } catch(e) {}
    }
    return results;
    """

    while len(all_tweet_data) < max_results:
        try:
            extracted_data = TWITTER_DRIVER.execute_script(collect_data_js)
            count_before = len(all_tweet_data)

            for item in (extracted_data or []):
                tweet_url = item.get('url', '')
                if not tweet_url or tweet_url in all_tweet_data or tweet_url in _SEEN_URLS:
                    continue
                all_tweet_data[tweet_url] = item

            new_count = len(all_tweet_data) - count_before
            if new_count > 0:
                print(f"      [Scroll] {len(all_tweet_data)} Data terkumpul (+{new_count} baru)")

            if new_count == 0:
                clicked_retry = TWITTER_DRIVER.execute_script("""
                    let btns = document.querySelectorAll('div[data-testid="primaryColumn"] button');
                    for (let btn of btns) {
                        let txt = btn.innerText.toLowerCase();
                        if (txt.includes('retry') || txt.includes('coba lagi')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                """)
                
                if clicked_retry:
                    print("      [INFO] Jaringan Twitter melambat. Menekan tombol 'Retry / Coba lagi'...")
                    time.sleep(5)
                    continue

                no_new_count += 1
                if no_new_count >= max_no_new:
                    if len(all_tweet_data) < max_results and "&f=live" not in url:
                        print(f"    [INFO] Tab 'Top' (Populer) selesai ({len(all_tweet_data)} data). Beralih otomatis ke tab 'Latest' (Terbaru) untuk melengkapi kuota...")
                        url = url + "&f=live"
                        TWITTER_DRIVER.get(url)
                        no_new_count = 0
                        time.sleep(5)
                        continue
                    else:
                        print(f"    [INFO] Mentok maksimal! {max_no_new}x scroll tanpa data baru. Berhenti.")
                        break
            else:
                no_new_count = 0

            if len(all_tweet_data) >= max_results:
                break

            TWITTER_DRIVER.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2.0, 4.0))

            body_text = (TWITTER_DRIVER.execute_script("return document.body.innerText") or "").lower()
            error_keywords = ["something went wrong", "ada yang salah", "try reloading", "kesalahan teknis", "muat ulang", "rate limit", "batas frekuensi", "batas terlampaui", "cannot retrieve", "tidak dapat memuat"]
            if any(err in body_text for err in error_keywords):
                print("\n    [!] PERINGATAN: Twitter menampilkan pesan limit/error di tengah scroll.")
                if "rate limit" in body_text or "batas" in body_text:
                    print("    [WARN] Akun Anda sedang terkena Rate Limit scroll dari Twitter.")
                    print("    [INFO] Anda bisa menunggu 10-15 menit atau mengganti akun Twitter di jendela Chrome.")
                else:
                    print("    [INFO] Cek jendela Chrome Anda: pastikan halaman pencarian dapat memuat tweet.")
                
                print("\n" + "=" * 60)
                print("🚨 PERIKSA BROWSER TWITTER (X) 🚨")
                print("1. Lihat jendela Chrome yang sedang berjalan.")
                print("2. Jika perlu login ulang / ganti akun, silakan lakukan langsung di Chrome tersebut.")
                print("3. Setelah tweet muncul normal kembali, tekan ENTER di terminal ini.")
                print("=" * 60 + "\n")
                
                input("👉 TEKAN ENTER SETELAH BROWSER NORMAL KEMBALI... ")
                
                print("    [INFO] Melanjutkan pencarian...")
                TWITTER_DRIVER.get(url)
                time.sleep(5)
                continue

            new_height = TWITTER_DRIVER.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                time.sleep(2)
                new_height = TWITTER_DRIVER.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_new_count += 1
            last_height = new_height

        except KeyboardInterrupt:
            print("\n    [!] Jeda / Ctrl+C terdeteksi. Menyimpan data yang sudah terkumpul sejauh ini...")
            break
        except Exception as e:
            print(f"    [WARN] Error saat scroll: {e}")
            break

    print(f"    [INFO] Selesai. Total {len(all_tweet_data)} data tweet berhasil diekstrak.")
    
    # Format hasil akhir
    final_data = []
    for item in all_tweet_data.values():
        date_str = item['date']
        clean_text = item['text'].replace('\n', ' ').replace('\r', ' ')
        
        final_data.append({
            'platform': 'Twitter',
            'keyword': keyword,
            'url': item['url'],
            'handle': item['username'],
            'content': clean_text,
            'created_at': _to_wib(date_str),
            'likes': item['likes'],
            'comments': item['replies'],
            'reposts': item['retweets'],
            'views': item['views'],
            'scraped_at': datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB',
        })
        _SEEN_URLS.add(item['url'])

    return final_data


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("[TEST] Memulai test scrape Twitter (Selenium - 2 Fase)...")
    reset_tracking()
    data = scrape_twitter("Kementerian Pekerjaan Umum", max_results=10)
    print(f"Berhasil ambil {len(data)} data")
    for d in data:
        print(f" -> {d['handle']} | Likes: {d['likes']} | {d['created_at']} | Content: {str(d['content'])[:50]}...")
    if TWITTER_DRIVER:
        TWITTER_DRIVER.quit()
