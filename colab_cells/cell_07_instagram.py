# ============================================================
# CELL 7: SCRAPING INSTAGRAM (SELENIUM UNDETECTED)
# - Multi-hashtag per keyword untuk volume lebih banyak
# - Deduplikasi URL global (tidak scrape post yang sama 2x)
# - Konversi waktu ke WIB
# - Tracking hashtag yang sudah dikunjungi
# ============================================================
import time
import os
import re
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
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.common.action_chains import ActionChains
except ImportError:
    pass

try:
    from cell_02_config import detect_topic, is_relevant_topic, IG_COOKIE
except ImportError:
    detect_topic = None
    is_relevant_topic = None
    IG_COOKIE = None

IG_DRIVER = None

# Path untuk Chrome profile persisten (login disimpan)
IG_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".ig_scraper_profile")

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

# ---- Global tracking ----
_VISITED_HASHTAGS = set()   # Hashtag yang sudah pernah dibuka
_SEEN_URLS = set()          # URL post yang sudah pernah di-scrape


def reset_tracking():
    """Reset tracking (untuk awal run baru tanpa resume)."""
    global _VISITED_HASHTAGS, _SEEN_URLS
    _VISITED_HASHTAGS = set()
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


def _keyword_to_hashtags(keyword):
    """
    Convert keyword riset ke daftar hashtag Instagram yang relevan.
    Untuk TA Elektrifikasi Kendaraan:
    - Menghasilkan hashtag spesifik dari keyword.
    - Menambahkan hashtag payung/populer yang aktif di Instagram
      agar pencarian tidak 'No Results', lalu difilter ketat oleh detect_topic().
    """
    global _VISITED_HASHTAGS
    import sys

    kw_lower = keyword.lower().strip()
    full_tag = kw_lower.replace(" ", "").replace("#", "")

    candidates = [full_tag]

    # Pemetaan hashtag aktif di Instagram untuk topik Elektrifikasi Kendaraan
    EV_HASHTAG_MAP = {
        'mobil': ['mobillistrik', 'mobillistrikindonesia', 'evindonesia', 'wulingairev', 'hyundaiioniq5', 'bydindonesia'],
        'motor': ['motorlistrik', 'motorlistrikindonesia', 'motorlistrikmurah', 'gesits', 'polytronfoxr', 'alvaone'],
        'spklu': ['spklu', 'plnspklu', 'spkluindonesia'],
        'baterai': ['baterailistrik', 'bateraimobillistrik', 'swapbaterai'],
        'kendaraan': ['kendaraanlistrik', 'elektrifikasikendaraan', 'evindonesia'],
        'listrik': ['kendaraanlistrik', 'mobillistrik', 'motorlistrik'],
        'elektrifikasi': ['elektrifikasikendaraan', 'kendaraanlistrik', 'evindonesia'],
    }

    # Pemetaan hashtag aktif di Instagram untuk topik Kemen PU & Menteri PU
    PU_HASHTAG_MAP = {
        'pu': ['kemenpu', 'kemenpuri', 'kementerianpekerjaanumum', 'pekerjaanumum', 'kemenpupr', 'pupr'],
        'kemenpu': ['kemenpu', 'kemenpuri', 'kementerianpekerjaanumum', 'pekerjaanumum'],
        'menteri': ['menteripu', 'menteripekerjaanumum', 'dodyhanggodo', 'menpu', 'menteridody'],
        'dody': ['dodyhanggodo', 'menteripu', 'menpu'],
        'hanggodo': ['dodyhanggodo', 'menteripu'],
        'pekerjaan': ['pekerjaanumum', 'kementerianpekerjaanumum', 'kemenpu', 'kemenpuri'],
        'umum': ['pekerjaanumum', 'kemenpu', 'kemenpuri'],
        'infrastruktur': ['infrastruktur', 'kemenpu', 'pekerjaanumum', 'sigapmembangunnegeri'],
        'jalan': ['binamarga', 'jalantol', 'kemenpu', 'pekerjaanumum', 'jalanrusak'],
        'bendungan': ['sumberdayaair', 'sda', 'bendungan', 'kemenpu'],
        'banjir': ['sda', 'bbws', 'kemenpu', 'banjir'],
        'irigasi': ['sda', 'irigasi', 'kemenpu'],
        'cipta karya': ['ciptakarya', 'kemenpu'],
        'bina marga': ['binamarga', 'kemenpu'],
        'wamen': ['wamenpu', 'dianakusumastuti', 'kemenpu'],
        'diana': ['dianakusumastuti', 'wamenpu'],
    }

    is_ta_mode = (os.environ.get('PROJECT_MODE') == 'ELEKTRIFIKASI' 
                  or any(arg in sys.argv for arg in ['--ta', '--elektrifikasi']))

    if is_ta_mode:
        for pattern, tags in EV_HASHTAG_MAP.items():
            if pattern in kw_lower:
                candidates.extend(tags)
        candidates.extend(['kendaraanlistrik', 'mobillistrik', 'motorlistrik', 'spklu', 'evindonesia'])
    else:
        for pattern, tags in PU_HASHTAG_MAP.items():
            if pattern in kw_lower:
                candidates.extend(tags)
        # Tambahan hashtag umum Kemen PU jika belum ada
        candidates.extend(['kemenpu', 'kemenpuri', 'pekerjaanumum', 'menteripu'])

    # Deduplikasi kandidat hashtag
    seen = set()
    result = []
    for tag in candidates:
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)

    return result


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
    """Membuat instance ChromeOptions baru setiap pemanggilan agar tidak terkena error reuse."""
    options = uc.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=id-ID,id,en-US,en')

    # Anti-Occlusion & Background Execution:
    # Memastikan Chrome tetap aktif 100% saat ditimpa oleh aplikasi lain (VS Code, Word, Browser lain, dll.)
    # Selama jendela Chrome TIDAK di-minimize ke taskbar, Chrome tidak akan di-throttle atau di-freeze oleh Windows OS.
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,ThrottleDisplayNoneAndDisplayInlineCSS')

    options.add_argument(f'--user-data-dir={IG_PROFILE_DIR}')
    return options


def _init_driver():
    """Buat driver baru dengan profile persisten."""
    global IG_DRIVER
    # Tutup driver lama jika ada
    if IG_DRIVER is not None:
        try:
            IG_DRIVER.quit()
        except:
            pass
        IG_DRIVER = None

    import socket
    socket.setdefaulttimeout(30)

    major_v = _get_chrome_major_version()
    driver_started = False

    if major_v:
        try:
            IG_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=major_v)
            driver_started = True
        except Exception as e:
            time.sleep(1)

    if not driver_started:
        try:
            IG_DRIVER = uc.Chrome(options=_build_chrome_options())
            driver_started = True
        except Exception:
            time.sleep(1)

    if not driver_started and major_v:
        for fallback_v in [major_v - 1, major_v - 2]:
            try:
                IG_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=fallback_v)
                driver_started = True
                break
            except Exception:
                pass

    if not driver_started or IG_DRIVER is None:
        raise RuntimeError("Gagal membuka Chrome Selenium untuk Instagram.")

    # Cek apakah sudah login (profile persisten)
    IG_DRIVER.get("https://www.instagram.com/")
    time.sleep(4)
    # Cek apakah sudah login berdasarkan keberadaan cookie 'sessionid'
    cookies = IG_DRIVER.get_cookies()
    is_logged_in = any(c.get('name') == 'sessionid' for c in cookies)

    # Injeksi cookie otomatis dari konfigurasi jika sessionid belum ada
    if not is_logged_in and IG_COOKIE:
        print("    [INFO] Mencoba login otomatis via injeksi IG_COOKIE...")
        try:
            for item in IG_COOKIE.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    IG_DRIVER.add_cookie({
                        'name': k.strip(),
                        'value': v.strip(),
                        'domain': '.instagram.com',
                        'path': '/'
                    })
            IG_DRIVER.get("https://www.instagram.com/")
            time.sleep(3)
            cookies = IG_DRIVER.get_cookies()
            is_logged_in = any(c.get('name') == 'sessionid' for c in cookies)
            current_url = IG_DRIVER.current_url
            if is_logged_in and "/challenge" not in current_url and "/accounts/login" not in current_url:
                print("    [OK] Injeksi cookie berhasil! Berhasil login otomatis ke Instagram.")
        except Exception as e_cook:
            print(f"    [WARN] Injeksi cookie gagal: {e_cook}")

    current_url = IG_DRIVER.current_url
    if not is_logged_in or "/challenge" in current_url:
        print("\n" + "="*60)
        print("🚨 TINDAKAN DIBUTUHKAN (INSTAGRAM) 🚨")
        print("1. Jendela Chrome sudah terbuka.")
        print("2. Silakan LOGIN dan SELESAIKAN CAPTCHA/2FA secara MANUAL.")
        print("3. JANGAN tekan Enter sebelum Anda masuk ke Beranda IG!")
        print("4. Setelah login, sesi akan TERSIMPAN (tidak perlu login lagi).")
        print("="*60 + "\n")

        input("👉 TEKAN ENTER DI SINI JIKA SUDAH SELESAI LOGIN & CAPTCHA... ")
        print("    [OK] Melanjutkan ke pencarian...")
        time.sleep(2)
    else:
        print("    [OK] Sesi login tersimpan! Otomatis masuk tanpa login ulang.")

    return IG_DRIVER


def _search_urls_via_google(keyword, max_urls=200):
    """
    Cari URL Instagram via Google site search.
    Menemukan postingan yang menyebut keyword di CAPTION, bukan cuma hashtag.
    Google mengindex Instagram jauh lebih baik dari DuckDuckGo.
    """
    global _SEEN_URLS
    # pyrefly: ignore [missing-import]
    from googlesearch import search

    found_urls = []
    found_set = set()

    # Variasi query untuk hasil lebih banyak
    queries = [
        f'site:instagram.com/p/ "{keyword}"',
        f'site:instagram.com/reel/ "{keyword}"',
        f'site:instagram.com "{keyword}" instagram',
    ]

    for query in queries:
        if len(found_urls) >= max_urls:
            break

        print(f"      [GOOGLE] Mencari: {query}")
        try:
            results = search(query, num_results=min(100, max_urls - len(found_urls)), lang="id")
            for link in results:
                # Filter hanya URL post/reel Instagram
                if ('instagram.com/p/' in link or 'instagram.com/reel/' in link):
                    clean_url = link.split('?')[0]
                    if not clean_url.endswith('/'):
                        clean_url += '/'
                    if clean_url not in found_set and clean_url not in _SEEN_URLS:
                        found_urls.append(clean_url)
                        found_set.add(clean_url)

            print(f"      [GOOGLE] +{len(found_urls)} URL ditemukan sejauh ini")
        except Exception as e:
            print(f"      [GOOGLE WARN] Error pada query '{query}': {e}")

        # Jeda antar query agar tidak diblokir Google
        time.sleep(random.uniform(3.0, 6.0))

    print(f"      [GOOGLE] Total {len(found_urls)} URL unik dari Google")
    return found_urls


def scrape_instagram(keyword, max_results=50, use_google=False, use_hashtag=True, on_item_scraped=None):
    global IG_DRIVER, _VISITED_HASHTAGS, _SEEN_URLS

    print(f"    - Instagram Selenium: mencari '{keyword}'...")

    if IG_DRIVER is None:
        print("    [!] Membuka Chrome untuk Instagram pertama kali...")
        _init_driver()

    # ========== FASE 1: KUMPULKAN URL ==========
    MIN_URLS = max_results
    all_post_urls = []
    all_urls_set = set()
    hashtag_url_counts = {}

    # --- Metode 1: Google Site Search (keyword di caption) ---
    if use_google:
        print("    [FASE 1A] Pencarian keyword via Google site:instagram.com ...")
        google_urls = _search_urls_via_google(keyword, max_urls=max_results)
        for url in google_urls:
            if url not in all_urls_set and url not in _SEEN_URLS:
                all_post_urls.append(url)
                all_urls_set.add(url)
        print(f"    [GOOGLE] {len(all_post_urls)} URL baru dari keyword search")

    # --- Metode 2: Hashtag Search (jika masih kurang) ---
    if use_hashtag and len(all_post_urls) < MIN_URLS:
        print(f"    [FASE 1B] Hashtag search (masih butuh {MIN_URLS - len(all_post_urls)} URL lagi)...")

        hashtags = _keyword_to_hashtags(keyword)
        if hashtags:
            print(f"    - Hashtags: {['#' + h for h in hashtags]}")

            def _scroll_hashtag_page(hashtag, target_count):
                """Scroll halaman hashtag dan kumpulkan URL. Return jumlah URL baru."""
                nonlocal all_post_urls, all_urls_set

                tag_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                print(f"      [Hashtag] Membuka #{hashtag} (target: {target_count} URL)...")

                try:
                    IG_DRIVER.get(tag_url)
                    time.sleep(3)

                    body_text = IG_DRIVER.execute_script(
                        "return (document.body && document.body.innerText) || ''"
                    ) or ""
                    body_lower = body_text.lower()
                    if ("tidak tersedia" in body_lower
                            or "isn't available" in body_lower
                            or "sorry, this page" in body_lower
                            or "no results" in body_lower
                            or "we couldn't find anything" in body_lower
                            or "belum ada postingan" in body_lower
                            or "no posts yet" in body_lower):
                        print(f"      [!] #{hashtag} tidak ditemukan (No Results). Skip.")
                        return 0

                    scroll_attempts = 0
                    max_scroll = 15
                    prev_total = len(all_post_urls)

                    while (len(all_post_urls) - prev_total) < target_count:
                        post_elements = IG_DRIVER.find_elements(
                            By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']"
                        )
                        count_before = len(all_post_urls)

                        for el in post_elements:
                            try:
                                href = el.get_attribute('href')
                                if (href
                                        and '/c/' not in href
                                        and href not in _SEEN_URLS
                                        and href not in all_urls_set):
                                    all_post_urls.append(href)
                                    all_urls_set.add(href)
                            except:
                                pass

                        new_from_this = len(all_post_urls) - prev_total
                        total_now = len(all_post_urls)
                        print(f"      - #{hashtag}: +{new_from_this} URL (total keseluruhan: {total_now}/{MIN_URLS})...")

                        if new_from_this >= target_count:
                            break

                        if len(all_post_urls) == count_before:
                            scroll_attempts += 1
                            if scroll_attempts >= max_scroll:
                                print(f"      [!] #{hashtag}: Mentok setelah {max_scroll}x scroll tanpa URL baru.")
                                break
                        else:
                            scroll_attempts = 0

                        try:
                            # Scroll dan pemicu synthetic event agar infinite scroll React IG tetap aktif meski ditimpa window lain
                            IG_DRIVER.execute_script("""
                                window.scrollBy(0, 3000);
                                window.dispatchEvent(new Event('scroll'));
                            """)
                            if post_elements:
                                try:
                                    IG_DRIVER.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'end'});", post_elements[-1])
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        time.sleep(random.uniform(2.0, 3.5))

                    new_total = len(all_post_urls) - prev_total
                    print(f"      [Hashtag] #{hashtag}: {new_total} URL baru dikumpulkan.")
                    return new_total

                except Exception as e:
                    print(f"      [WARN] Error pada #{hashtag}: {e}")
                    return 0

            for hashtag in hashtags:
                _VISITED_HASHTAGS.add(hashtag)
                remaining = MIN_URLS - len(all_post_urls)
                if remaining <= 0:
                    break
                target = max(remaining, 40)
                count = _scroll_hashtag_page(hashtag, target)
                hashtag_url_counts[hashtag] = count

                if len(all_post_urls) >= MIN_URLS:
                    print(f"    [✓] Sudah mencapai {len(all_post_urls)} URL (>= {MIN_URLS}). Lanjut ke Fase 2.")
                    break
        else:
            print(f"    [SKIP] Semua hashtag untuk '{keyword}' sudah pernah dikunjungi.")

    # Limit ke max_results
    all_post_urls = all_post_urls[:max_results]
    print(f"    [INFO] Fase 1 Selesai. Total {len(all_post_urls)} URL unik (DDG + Hashtag).")

    if not all_post_urls:
        return []

    # ========== FASE 2: EKSTRAKSI DATA DI TAB BARU ==========
    print("    [INFO] Fase 2: Mulai ekstraksi data di Tab Baru...")
    results = []
    main_window = IG_DRIVER.current_window_handle
    consecutive_failures = 0

    for idx, url_post in enumerate(all_post_urls):
        print(f"      [{idx+1}/{len(all_post_urls)}] Ekstraksi: {url_post}")

        # Stop jika 5x berturut-turut gagal (kemungkinan diblokir)
        if consecutive_failures >= 5:
            print("      [!] 5x berturut-turut gagal. Kemungkinan diblokir. Berhenti untuk keyword ini.")
            break

        try:
            # 1. Buka tab baru
            IG_DRIVER.execute_script(f"window.open('{url_post}', '_blank');")
            time.sleep(1)

            # 2. Pindah ke Tab Baru
            if len(IG_DRIVER.window_handles) > 1:
                IG_DRIVER.switch_to.window(IG_DRIVER.window_handles[-1])
            else:
                print("      [WARN] Tab baru gagal terbuka. Skip.")
                continue

            # 3. Tunggu halaman loading
            try:
                WebDriverWait(IG_DRIVER, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except:
                pass

            # Jeda agar React SPA selesai render (dibuat lebih cepat)
            time.sleep(random.uniform(1.0, 3.0))

            # 4. Debug info
            page_title = IG_DRIVER.title or ""
            page_url = IG_DRIVER.current_url or ""
            body_text = IG_DRIVER.execute_script(
                "return (document.body && document.body.innerText) || ''"
            ) or ""
            body_preview = body_text[:300].replace('\n', ' | ')

            print(f"        [DEBUG] Title: {page_title[:80]}")
            print(f"        [DEBUG] URL: {page_url}")
            print(f"        [DEBUG] Body (300 char): {body_preview[:150]}...")

            # Cek error page
            body_lower = body_text.lower()
            if "error 429" in body_lower or "too many requests" in body_lower:
                print("      [!!!] HTTP ERROR 429 Terdeteksi! Meminta pergantian akun...")
                try:
                    IG_DRIVER.delete_all_cookies()
                    IG_DRIVER.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                except:
                    pass
                IG_DRIVER.get("https://www.instagram.com/accounts/login/")
                print("      =====================================================")
                print("      [ACTION REQUIRED] Silakan login dengan AKUN BARU di Chrome yang terbuka.")
                input("      [ACTION REQUIRED] Tekan ENTER di terminal ini jika sudah berhasil masuk ke feed...")
                print("      =====================================================")
                consecutive_failures += 1
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                
                # Coba refresh halaman utama agar ikut menggunakan sesi baru
                try:
                    IG_DRIVER.refresh()
                    time.sleep(5)
                except:
                    pass

                if consecutive_failures >= 3:
                     print("      [!!!] Rate Limit membandel. Lanjut ke hashtag/keyword berikutnya.")
                     return results
                continue
            elif "isn't working" in body_lower or "tidak tersedia" in body_lower or "page not found" in body_lower or "can’t be reached" in body_lower or "can't be reached" in body_lower or "err_quic" in body_lower or "err_timed_out" in body_lower:
                print("      [!] Halaman error/tidak tersedia. Skip.")
                consecutive_failures += 1
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                time.sleep(random.uniform(0.5, 1.5))
                continue

            # Cek redirect ke login
            if "/accounts/login" in page_url or "/challenge/" in page_url:
                print("      [!] Halaman redirect ke login/challenge. Skip.")
                consecutive_failures += 1
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                time.sleep(random.uniform(0.5, 1.5))
                continue

            # 5. Ekstrak data — JavaScript MULTI-SOURCE & AUTO-EXPAND
            js_extract = """
            return (function() {
                let data = {
                    handle: '',
                    content: '',
                    date: '',
                    likes: 0,
                    comments: 0,
                    views: 0,
                    is_video: false,
                    is_truncated: false,
                    source: ''
                };

                // A. KLIK TOMBOL 'MORE' / 'SELENGKAPNYA' / 'SEE MORE' SEBELUM BACA DOM
                try {
                    let expandCandidates = document.querySelectorAll(
                        'article span[role="button"], article div[role="button"], article button, ' +
                        'main span[role="button"], main div[role="button"], main button, ' +
                        'span[role="button"], div[role="button"], button, span'
                    );
                    expandCandidates.forEach(el => {
                        if (el.tagName === 'A' || el.closest('a')) return;
                        let t = (el.innerText || '').trim().toLowerCase();
                        let isMore = /^(?:…|\\.\\.\\.)?\\s*(more|selengkapnya|see more|lihat selengkapnya)\\s*$/i.test(t) ||
                                     t.endsWith('more') || t.endsWith('selengkapnya');
                        if (isMore) {
                            try {
                                ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(evt => {
                                    el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                                });
                                el.click();
                            } catch(e) {}
                        }
                    });
                } catch(e) {}

                // B. HANDLE (Username)
                let handleSelectors = [
                    'header a[href*="/"] span',
                    'header a[role="link"]',
                    'header a',
                    'h2 a',
                    'article header a',
                    'a[href*="/"] > span > span',
                    'article a[href*="/"]'
                ];
                for (let sel of handleSelectors) {
                    let el = document.querySelector(sel);
                    if (el) {
                        let txt = el.innerText.trim();
                        if (txt && txt.length < 40 && !txt.includes(' ') && !txt.includes('\\n')) {
                            data.handle = txt;
                            break;
                        }
                    }
                }
                if (!data.handle) {
                    let ogUrl = document.querySelector('meta[property="og:url"]');
                    if (ogUrl) {
                        let match = ogUrl.content.match(/instagram\\.com\\/([^/]+)/);
                        if (match && match[1] !== 'p' && match[1] !== 'reel') {
                            data.handle = match[1];
                        }
                    }
                }
                if (!data.handle) {
                    let title = document.title || '';
                    let titleMatch = title.match(/^(.+?)\\s+on Instagram/i) || title.match(/^(.+?)\\s+di Instagram/i) || title.match(/^(.+?)\\s*\\(@/);
                    if (titleMatch) {
                        data.handle = titleMatch[1].trim();
                    }
                }

                // C. AMBIL CAPTION LENGKAP DARI BERBAGAI SUMBER
                let candidates = [];

                // 1. Sumber Schema.org JSON-LD (SANGAT LENGKAP & TIDAK PERNAH DI-TRUNCATE OLEH META)
                try {
                    let jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
                    jsonLdScripts.forEach(s => {
                        try {
                            let j = JSON.parse(s.innerText || '{}');
                            let body = j.articleBody || j.caption || j.description || j.text;
                            if (body && typeof body === 'string' && body.trim().length > 10) {
                                candidates.push({ text: body.trim(), source: 'json-ld' });
                            }
                        } catch(e) {}
                    });
                } catch(e) {}

                // 2. Sumber Script Inline (GraphQL / React Store)
                try {
                    let scripts = document.querySelectorAll('script');
                    for (let s of scripts) {
                        let txt = s.innerText || '';
                        if (txt.includes('"caption"') && (txt.includes('"text"') || txt.includes('edge_media_to_caption'))) {
                            let m = txt.match(/"caption"\\s*:\\s*\\{\\s*"text"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"/);
                            if (m && m[1]) {
                                try {
                                    let decoded = JSON.parse('"' + m[1] + '"');
                                    if (decoded && decoded.length > 10) {
                                        candidates.push({ text: decoded.trim(), source: 'graphql-script' });
                                    }
                                } catch(e) {}
                            }
                        }
                    }
                } catch(e) {}

                // 3. Sumber DOM yang sudah di-expand (h1, div._a9zs, span._ap3a)
                let h1El = document.querySelector('h1');
                if (h1El) {
                    let h1Text = h1El.innerText.trim();
                    if (data.handle && h1Text.startsWith(data.handle)) {
                        h1Text = h1Text.substring(data.handle.length).trim();
                    }
                    if (h1Text.length > 10) {
                        candidates.push({ text: h1Text, source: 'dom-h1' });
                    }
                }

                let a9zs = document.querySelectorAll('div._a9zs, div[class*="_a9zs"]');
                a9zs.forEach(el => {
                    let txt = el.innerText.trim();
                    if (txt.length > 10) {
                        candidates.push({ text: txt, source: 'dom-a9zs' });
                    }
                });

                let ap3a = document.querySelectorAll('span._ap3a');
                ap3a.forEach(el => {
                    let txt = el.innerText.trim();
                    if (txt.length > 15 && !txt.includes('likes') && !txt.includes('suka') && !txt.includes('Follow')) {
                        candidates.push({ text: txt, source: 'dom-span-ap3a' });
                    }
                });

                // 4. Sumber Meta Tag (Fallback)
                let metaDesc = document.querySelector('meta[name="description"]');
                if (metaDesc) {
                    let desc = metaDesc.getAttribute('content') || '';
                    let colonIdx = desc.indexOf(': ');
                    if (colonIdx > -1 && colonIdx < desc.length - 5) {
                        candidates.push({ text: desc.substring(colonIdx + 2).replace(/"/g, '').trim(), source: 'meta-description' });
                    }
                }

                // Pembersihan teks kandidat
                let cleanText = function(t) {
                    if (!t) return '';
                    t = t.replace(/\\s*(?:…|\\.\\.\\.)?\\s*(?:more|selengkapnya|lihat selengkapnya)\\s*$/i, '');
                    return t.trim();
                };

                candidates = candidates.map(c => ({
                    text: cleanText(c.text),
                    source: c.source
                })).filter(c => c.text.length > 5);

                // Urutkan berdasarkan panjang karakter menurun (ambil caption terpanjang)
                candidates.sort((a, b) => b.text.length - a.text.length);

                if (candidates.length > 0) {
                    data.content = candidates[0].text;
                    data.source = candidates[0].source;
                }

                // Cek apakah caption masih terindikasi terpotong
                if (data.content) {
                    let endsDots = /(?:…|\\.\\.\\.)$/.test(data.content);
                    let hasMoreWord = /\\b(more|selengkapnya)\\b/i.test(data.content.slice(-30));
                    data.is_truncated = endsDots || hasMoreWord;
                }

                // D. DATE
                let timeEl = document.querySelector('time[datetime]');
                if (timeEl) {
                    data.date = timeEl.getAttribute('datetime');
                }

                // E. ENGAGEMENT (MULTI-SOURCE: JSON-LD + GRAPHQL + META + DOM + REELS)
                function parseCount(str) {
                    if (!str) return 0;
                    let s = str.toLowerCase().replace(/,/g, '.').replace(/\\s+/g, '');
                    let m = s.match(/([\\d.]+)([kmrbjtribuja]*)/);
                    if (!m) return 0;
                    let val = parseFloat(m[1]);
                    if (isNaN(val)) return 0;
                    let unit = m[2];
                    if (unit.includes('k') || unit.includes('rb') || unit.includes('ribu')) val *= 1000;
                    else if (unit.includes('m') || unit.includes('jt') || unit.includes('juta')) val *= 1000000;
                    return Math.round(val);
                }

                // 1. JSON-LD interactionStatistic
                try {
                    let ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
                    ldScripts.forEach(s => {
                        try {
                            let j = JSON.parse(s.innerText || '{}');
                            if (j.interactionStatistic) {
                                let stats = Array.isArray(j.interactionStatistic) ? j.interactionStatistic : [j.interactionStatistic];
                                stats.forEach(st => {
                                    let iType = (st.interactionType || '').toLowerCase();
                                    let cnt = parseInt(st.userInteractionCount || 0);
                                    if (cnt > 0) {
                                        if (iType.includes('like')) data.likes = Math.max(data.likes, cnt);
                                        if (iType.includes('comment')) data.comments = Math.max(data.comments, cnt);
                                    }
                                });
                            }
                        } catch(e) {}
                    });
                } catch(e) {}

                // 2. Inline GraphQL / Script Tags
                try {
                    let scs = document.querySelectorAll('script');
                    for (let s of scs) {
                        let txt = s.innerText || '';
                        if (txt.includes('edge_media_preview_like') || txt.includes('like_count')) {
                            let mLike = txt.match(/"edge_media_preview_like"\\s*:\\s*\\{\\s*"count"\\s*:\\s*(\\d+)/) ||
                                        txt.match(/"like_count"\\s*:\\s*(\\d+)/) ||
                                        txt.match(/"edge_liked_by"\\s*:\\s*\\{\\s*"count"\\s*:\\s*(\\d+)/);
                            if (mLike && parseInt(mLike[1]) > 0) {
                                data.likes = Math.max(data.likes, parseInt(mLike[1]));
                            }
                            let mComm = txt.match(/"edge_media_to_comment"\\s*:\\s*\\{\\s*"count"\\s*:\\s*(\\d+)/) ||
                                        txt.match(/"comment_count"\\s*:\\s*(\\d+)/);
                            if (mComm && parseInt(mComm[1]) > 0) {
                                data.comments = Math.max(data.comments, parseInt(mComm[1]));
                            }
                        }
                    }
                } catch(e) {}

                // 3. Meta Description (OpenGraph / Google)
                let metaDesc2 = document.querySelector('meta[name="description"], meta[property="og:description"]');
                if (metaDesc2) {
                    let descText = metaDesc2.getAttribute('content') || '';
                    let likeMatch = descText.match(/([\\d,.\\u00a0]+)\\s*(likes|suka|Likes)/i);
                    if (likeMatch) {
                        let parsed = parseInt(likeMatch[1].replace(/[,.\\u00a0]/g, ''));
                        if (parsed > 0) data.likes = Math.max(data.likes, parsed);
                    }
                    
                    let commentMatch = descText.match(/([\\d,.\\u00a0]+)\\s*(comments|komentar|Comments)/i);
                    if (commentMatch) {
                        let parsed = parseInt(commentMatch[1].replace(/[,.\\u00a0]/g, ''));
                        if (parsed > 0) data.comments = Math.max(data.comments, parsed);
                    }
                    
                    let viewMatch = descText.match(/([\\d,.\\u00a0]+)\\s*(plays|views|tayangan|kali diputar|Plays|Views)/i);
                    if (viewMatch) {
                        let parsed = parseInt(viewMatch[1].replace(/[,.\\u00a0]/g, ''));
                        if (parsed > 0) data.views = Math.max(data.views, parsed);
                    }
                }

                // 4. Link a[href*="/liked_by/"]
                if (data.likes === 0) {
                    let likedByLinks = document.querySelectorAll('a[href*="/liked_by/"], a[href*="/liked_by"]');
                    for (let lk of likedByLinks) {
                        let parsed = parseCount(lk.innerText || '');
                        if (parsed > 0) {
                            data.likes = parsed;
                            break;
                        }
                    }
                }

                // 5. Section Spans ("Disukai oleh ... dan X lainnya" atau "X suka")
                if (data.likes === 0) {
                    let sectionSpans = Array.from(document.querySelectorAll('section span, section a span, section div span, button span'));
                    for (let s of sectionSpans) {
                        let t = (s.innerText || '').toLowerCase().trim();
                        if (t.includes('suka') || t.includes('like') || t.includes('lainnya') || t.includes('others')) {
                            let m = t.match(/([\\d.,]+)\\s*(?:lainnya|others|suka|likes|orang)/i) || t.match(/(?:dan|and)\\s*([\\d.,]+)/i);
                            if (m) {
                                let parsed = parseCount(m[1]);
                                if (parsed > 0) {
                                    data.likes = parsed;
                                    break;
                                }
                            }
                        }
                    }
                }

                // 6. Reels Heart Button Sibling / Parent
                if (data.likes === 0) {
                    let heartSvgs = document.querySelectorAll('svg[aria-label*="Like"], svg[aria-label*="Suka"], svg[aria-label*="like"], svg[aria-label*="suka"]');
                    for (let hSvg of heartSvgs) {
                        let parentBtn = hSvg.closest('button') || hSvg.closest('div[role="button"]');
                        if (parentBtn) {
                            let parsed = parseCount(parentBtn.innerText || '');
                            if (parsed > 0) {
                                data.likes = parsed;
                                break;
                            }
                        }
                    }
                }

                if (document.querySelector('video')) {
                    data.is_video = true;
                }

                return data;
            })();
            """

            extracted = IG_DRIVER.execute_script(js_extract)

            # ============================================================
            # CROSSCHECK VERIFIKASI CAPTION: BUKA ULANG JIKA MASIH TERPOTONG
            # ============================================================
            curr_content = extracted.get('content', '') if extracted else ''
            is_trunc = extracted.get('is_truncated', False) if extracted else False

            if is_trunc or curr_content.endswith('...') or curr_content.endswith('…') or len(curr_content) < 50:
                print(f"        [CROSSCHECK TRIGGERED] Caption terindikasi belum lengkap ({len(curr_content)} char). Memverifikasi & re-expanding...")
                try:
                    # 1. Scroll dan coba klik ulang tombol 'more' / 'selengkapnya'
                    IG_DRIVER.execute_script("window.scrollBy(0, 300);")
                    time.sleep(0.4)
                    
                    more_btns = IG_DRIVER.find_elements(By.XPATH, "//*[text()='more' or text()='selengkapnya' or text()='See more' or text()='Lihat selengkapnya' or contains(text(), '... more') or contains(text(), '... selengkapnya')]")
                    for btn in more_btns:
                        try:
                            if btn.is_displayed():
                                try:
                                    ActionChains(IG_DRIVER).move_to_element(btn).click().perform()
                                except Exception:
                                    pass
                                try:
                                    IG_DRIVER.execute_script("arguments[0].click();", btn)
                                except Exception:
                                    pass
                                time.sleep(0.3)
                        except Exception:
                            pass

                    # Ekstrak ulang via JS setelah re-click
                    re_extracted = IG_DRIVER.execute_script(js_extract)
                    if re_extracted and len(re_extracted.get('content', '')) > len(curr_content):
                        print(f"        [CROSSCHECK OK] Caption berhasil diperluas via re-click: {len(curr_content)} -> {len(re_extracted.get('content'))} karakter!")
                        extracted = re_extracted
                        curr_content = extracted.get('content', '')
                except Exception as ex:
                    pass

                # 2. Jika MASIH terpotong atau kosong, muat ulang (reload) halaman secara langsung
                if curr_content.endswith('...') or curr_content.endswith('…') or len(curr_content) < 50:
                    print(f"        [CROSSCHECK DEEP] Memuat ulang post URL secara langsung untuk memastikan semua teks ter-render...")
                    try:
                        IG_DRIVER.get(url_post)
                        time.sleep(3.5)
                        deep_extracted = IG_DRIVER.execute_script(js_extract)
                        if deep_extracted and len(deep_extracted.get('content', '')) > len(curr_content):
                            print(f"        [CROSSCHECK OK] Caption berhasil diperluas via re-fetch: {len(curr_content)} -> {len(deep_extracted.get('content'))} karakter!")
                            extracted = deep_extracted
                    except Exception as ex:
                        print(f"        [CROSSCHECK WARN] Re-fetch gagal: {ex}")

            # Debug print
            print(f"        [DEBUG] Source: {extracted.get('source')} | handle='{extracted.get('handle')}' | likes={extracted.get('likes')} | views={extracted.get('views')} | date={extracted.get('date')}")
            print(f"        [DEBUG] Caption Length: {len(extracted.get('content', ''))} karakter")

            raw_caption = str(extracted.get('content', '')).strip()

            # 1. Pastikan caption tidak kosong dan bukan pesan error
            if not raw_caption or len(raw_caption) < 15:
                print(f"      [WARN] Caption terlalu pendek / kosong ({len(raw_caption)} char). Skip.")
                consecutive_failures += 1
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                continue

            # 2. Cek apakah caption masih terpotong (...)
            if raw_caption.endswith('...') or raw_caption.endswith('…'):
                print(f"      [WARN] Caption masih terpotong (...) setelah re-fetch. Skip agar tidak menyimpan teks buntung.")
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                continue

            # 3. REGULASI FILTER TOPIK (Kementerian_PU / Menteri_PU)
            matched_topic = detect_topic(raw_caption) if detect_topic else None
            if not matched_topic:
                c_snip = raw_caption[:45].replace('\n', ' ')
                print(f"      [FILTER REJECT] Postingan diabaikan karena bukan topik penelitian (Off-topic): '{c_snip}...'")
                _SEEN_URLS.add(url_post)
                IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                continue

            # 4. Postingan LOLOS Regulasi & Full Caption: Simpan ke hasil
            consecutive_failures = 0
            handle = extracted.get('handle', '') or 'instagram_user'

            created_at = _to_wib(extracted.get('date', ''))
            if not created_at:
                created_at = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB'

            is_vid = extracted.get('is_video', False)
            post_type = "Reel" if is_vid or "/reel/" in url_post or "/video/" in url_post else "Photo"

            # Bersihkan line terminators aneh (\u2028 LS, \u2029 PS, \r, dll) yang sering memicu warning di editor/VS Code
            clean_caption = re.sub(r'[\u2028\u2029\r\x0b\x0c\x85]', ' ', raw_caption)
            formatted_content = clean_caption.replace('\n', ' | ')
            formatted_content = re.sub(r'(\s*\|\s*)+', ' | ', formatted_content).strip(' |')

            results.append({
                "post_id": f"ig_{abs(hash(url_post)) % 1000000}",
                "platform": "Instagram",
                "post_type": post_type,
                "author": handle,
                "handle": f"@{handle}",
                "content": formatted_content,
                "description": "",
                "created_at": created_at,
                "likes": extracted.get('likes', 0),
                "comments": extracted.get('comments', 0),
                "url": url_post,
                "keyword": keyword,
                "scraped_at": datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB',
                "topic": matched_topic
            })

            # Mark URL as seen
            _SEEN_URLS.add(url_post)

            print(f"        ✨ [PASSED REGULASI] @{handle} | Topik: {matched_topic} | {len(raw_caption)} char | Likes: {extracted.get('likes', 0)}")
            extracted_data_count = len(results)

            if on_item_scraped:
                try:
                    on_item_scraped(results[-1])
                except Exception as cb_err:
                    print(f"        [CALLBACK WARN] Gagal menjalankan real-time save: {cb_err}")

            # 6. Tutup tab dan kembali ke halaman utama
            IG_DRIVER.close()
            IG_DRIVER.switch_to.window(main_window)

            # JEDA ACAK SETELAH MENUTUP TAB
            time.sleep(random.uniform(1.0, 2.0))

            # Istirahat setiap 30 post berhasil
            if len(results) > 0 and len(results) % 30 == 0:
                pause_time = random.uniform(5, 10)  # dipercepat jadi 5-10 detik
                print(f"      [PAUSE] Istirahat {int(pause_time)} detik setelah {len(results)} post (anti rate-limit)...")
                time.sleep(pause_time)

        except Exception as e:
            print(f"      [WARN] Gagal ekstrak {url_post}: {e}")
            consecutive_failures += 1
            try:
                # Pastikan kembali ke tab utama
                if len(IG_DRIVER.window_handles) > 1:
                    IG_DRIVER.close()
                IG_DRIVER.switch_to.window(main_window)
                time.sleep(2)
            except:
                pass
            continue

    print(f"    [INFO] Fase 2 Selesai. Total {len(results)} data berhasil diekstrak dari {len(all_post_urls)} URL.")
    return results


# ============================================================
# TEST
# ============================================================
# FUNGSI SCRAPING MENGGUNAKAN GRAMSCRAPER API
# ============================================================
import requests
import json
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

def scrape_instagram_api(keyword, max_results=50):
    """
    Scrape Instagram via GramScraper API.
    Keyword diubah menjadi hashtag (spasi dihilangkan).
    """
    global _SEEN_URLS
    
    load_dotenv()
    api_key = os.getenv("GRAMSCRAPER_API_KEY")
    
    if not api_key:
        print("    [!] ERROR: GRAMSCRAPER_API_KEY tidak ditemukan di .env!")
        return []
        
    hashtag = keyword.lower().replace(" ", "").replace("#", "")
    print(f"    - GramScraper API: mencari hashtag '#{hashtag}' (Target: {max_results} data)...")
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    results = []
    seen_in_this_run = set()
    next_page_id = None
    
    while len(results) < max_results:
        url = f"https://gramscraper.com/api/instagram/v2/hashtag/medias/recent?name={hashtag}"
        if next_page_id:
            url += f"&max_id={next_page_id}"
            
        try:
            print(f"      [API] Fetching dari GramScraper (Data terkumpul: {len(results)})...")
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                print(f"      [API] Request gagal: {res.status_code}")
                print(res.text)
                break
                
            data = res.json()
            
            items = data.get('response', [])
            if not isinstance(items, dict) or 'sections' not in items:
                print("      [API] Format response tidak sesuai harapan atau tidak ada data.")
                break
                
            new_posts = 0
            for section in items['sections']:
                layout = section.get('layout_content', {})
                medias = layout.get('medias', [])
                for m in medias:
                    if 'media' not in m:
                        continue
                        
                    p = m['media']
                    post_id = p.get('id')
                    code = p.get('code')
                    
                    if not code:
                        continue
                        
                    url_post = f"https://www.instagram.com/p/{code}/"
                    
                    if url_post in _SEEN_URLS or url_post in seen_in_this_run:
                        continue
                        
                    seen_in_this_run.add(url_post)
                    _SEEN_URLS.add(url_post)
                    
                    # Ekstrak data sesuai format CSV kita
                    user = p.get('user', {})
                    username = user.get('username', '')
                    fullname = user.get('full_name', '')
                    
                    caption_text = ""
                    caption_obj = p.get('caption')
                    if caption_obj and isinstance(caption_obj, dict):
                        caption_text = caption_obj.get('text', '')
                        
                    # Tanggal
                    taken_at = p.get('taken_at')
                    if taken_at:
                        # taken_at biasanya unix timestamp
                        dt = datetime.fromtimestamp(taken_at, tz=WIB)
                        created_at = dt.strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
                    else:
                        created_at = ""
                        
                    is_video = p.get('media_type') == 2 or p.get('media_type') == 8
                    post_type = 'Reel/Video' if is_video else 'Photo'
                    
                    post_data = {
                        'post_id': f"ig_{post_id}" if post_id else f"ig_{code}",
                        'platform': 'Instagram',
                        'post_type': post_type,
                        'author': fullname if fullname else username,
                        'handle': f"@{username}",
                        'content': caption_text.replace('\n', ' | '),
                        'description': '',
                        'created_at': created_at,
                        'likes': p.get('like_count', 0),
                        'comments': p.get('comment_count', 0),
                        'url': url_post,
                        'keyword': keyword,
                        'scraped_at': datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')
                    }
                    
                    results.append(post_data)
                    new_posts += 1
                    
                    if len(results) >= max_results:
                        break
                
                if len(results) >= max_results:
                    break
                    
            print(f"      [API] +{new_posts} post baru ditemukan.")
            
            # Cek paginasi
            if not data.get('next_page_id'):
                print("      [API] Tidak ada halaman selanjutnya (mentok).")
                break
                
            next_page_id = data.get('next_page_id')
            
            # Rate limiting API
            time.sleep(1)
            
        except Exception as e:
            print(f"      [API ERROR] {e}")
            break
            
    print(f"    [OK] Selesai scraping '{keyword}'. Total didapat: {len(results)}")
    return results

def enrich_single_instagram_post(url_post):
    """
    Membuka 1 URL postingan Instagram secara langsung dan mengambil 100% caption utuh
    dengan auto-expand 'more' / 'selengkapnya' serta multi-source crosscheck.
    Mengembalikan dict dengan data caption, likes, comments, author.
    """
    global IG_DRIVER
    if not url_post or 'instagram.com' not in url_post:
        return {}

    if IG_DRIVER is None:
        _init_driver()

    try:
        IG_DRIVER.get(url_post)
        time.sleep(random.uniform(2.5, 3.5))

        # 1. Cek Redirect ke Halaman Login / Challenge
        cur_url = IG_DRIVER.current_url.lower()
        if "/accounts/login" in cur_url or "/challenge" in cur_url:
            return {'status': 'RATE_LIMIT', 'error': 'Redirected to Instagram login / challenge page', 'content': ''}

        # 2. Cek Indikator Error 429 / Throttling / This page isn't working
        page_title = (IG_DRIVER.title or '').lower()
        try:
            body_txt = (IG_DRIVER.find_element(By.TAG_NAME, 'body').text or '').lower()
        except:
            body_txt = ''

        if any(err in page_title or err in body_txt for err in [
            "this page isn’t working", "this page isn't working", "http error 429",
            "too many requests", "please wait a few minutes before trying again",
            "try again later", "we limit how often", "kami membatasi seberapa sering"
        ]):
            return {'status': 'RATE_LIMIT', 'error': 'Instagram 429 Rate Limit (This page isn\'t working / Please wait)', 'content': ''}

        # 3. Cek apakah halaman benar-benar dihapus / privat
        if "sorry, this page isn't available" in body_txt or "halaman ini tidak tersedia" in body_txt:
            return {'status': 'DELETED', 'content': "Sorry, this page isn't available."}

        # JS Multi-source extract dengan blacklist error teks
        js_extract = """
        return (function() {
            let data = { handle: '', content: '', date: '', likes: 0, comments: 0, is_truncated: false, status: 'OK' };
            
            // Expand clicks
            try {
                let btns = document.querySelectorAll('article span[role="button"], article button, span[role="button"], button, span');
                btns.forEach(b => {
                    let t = (b.innerText || '').trim().toLowerCase();
                    if (/^(?:…|\\.\\.\\.)?\\s*(more|selengkapnya|see more|lihat selengkapnya)\\s*$/i.test(t) || t.endsWith('more') || t.endsWith('selengkapnya')) {
                        try {
                            ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(evt => b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window })));
                            b.click();
                        } catch(e) {}
                    }
                });
            } catch(e) {}

            let candidates = [];
            // JSON-LD
            try {
                document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                    try {
                        let j = JSON.parse(s.innerText || '{}');
                        let body = j.articleBody || j.caption || j.description || j.text;
                        if (body && typeof body === 'string' && body.trim().length > 10) candidates.push(body.trim());
                    } catch(e) {}
                });
            } catch(e) {}

            // DOM h1, div._a9zs, span._ap3a
            let h1 = document.querySelector('h1');
            if (h1 && h1.innerText.trim().length > 10) candidates.push(h1.innerText.trim());
            document.querySelectorAll('div._a9zs, span._ap3a').forEach(el => {
                let txt = el.innerText.trim();
                if (txt.length > 15) candidates.push(txt);
            });

            // Meta description
            let meta = document.querySelector('meta[name="description"]');
            if (meta) {
                let d = meta.getAttribute('content') || '';
                let idx = d.indexOf(': ');
                if (idx > -1) candidates.push(d.substring(idx + 2).replace(/"/g, '').trim());
            }

            // Blacklist filter teks error browser / limit
            let badRegex = /this page isn['’]t working|http error 429|too many requests|please wait a few minutes|try again later|something went wrong|sorry, this page isn['’]t available|halaman ini tidak tersedia|login • instagram/i;

            candidates = candidates.filter(t => !badRegex.test(t));
            candidates = candidates.map(t => t.replace(/\\s*(?:…|\\.\\.\\.)?\\s*(?:more|selengkapnya|lihat selengkapnya)\\s*$/i, '').trim()).filter(t => t.length > 5);
            candidates.sort((a, b) => b.length - a.length);
            if (candidates.length > 0) data.content = candidates[0];

            if (data.content) {
                data.is_truncated = /(?:…|\\.\\.\\.)$/.test(data.content) || /\\b(more|selengkapnya)\\b/i.test(data.content.slice(-30));
            }
            return data;
        })();
        """
        extracted = IG_DRIVER.execute_script(js_extract) or {}

        # Crosscheck jika terpotong
        if extracted.get('is_truncated') or (extracted.get('content') and (extracted['content'].endswith('...') or extracted['content'].endswith('…'))):
            try:
                more_btns = IG_DRIVER.find_elements(By.XPATH, "//*[text()='more' or text()='selengkapnya' or text()='See more' or text()='Lihat selengkapnya' or contains(text(), '... more') or contains(text(), '... selengkapnya')]")
                for btn in more_btns:
                    try:
                        if btn.is_displayed():
                            try:
                                ActionChains(IG_DRIVER).move_to_element(btn).click().perform()
                            except Exception:
                                pass
                            try:
                                IG_DRIVER.execute_script("arguments[0].click();", btn)
                            except Exception:
                                pass
                            time.sleep(0.3)
                    except:
                        pass
                re_ext = IG_DRIVER.execute_script(js_extract) or {}
                if re_ext and len(re_ext.get('content', '')) > len(extracted.get('content', '')):
                    extracted = re_ext
            except:
                pass

        return extracted
    except Exception as e:
        print(f"    [WARN] Enrich failed for {url_post}: {e}")
        return {}


# ============================================================
if __name__ == "__main__":
    print("[TEST] Memulai test scrape Instagram (Selenium)...")
    reset_tracking()
    data = scrape_instagram("Kementerian Pekerjaan Umum", max_results=5)
    print(f"Berhasil ambil {len(data)} data")
    for d in data:
        print(f" -> {d['handle']} | Likes: {d['likes']} | {d['created_at']} | Content: {str(d['content'])[:50]}...")
    if IG_DRIVER:
        IG_DRIVER.quit()
