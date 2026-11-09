from cell_02_config import *
# ============================================================
# CELL 8: SCRAPER THREADS (SELENIUM UNDETECTED) — v3
# - Tab "Recent" (bukan Top) untuk hasil lebih relevan
# - Single-Phase: Scroll + Ekstraksi langsung dari DOM
# - Filter tanggal: 1 Januari 2025 - sekarang
# - Filter konten: skip post yang tidak relevan dengan keyword
# - Profil persisten (login tersimpan)
# - Anti-throttling background tab
# - Deteksi rate limit / login wall
# - Clean single-line CSV output
# - Auto-resume support via run_threads_only.py
# ============================================================

import time
import urllib.parse
import os
import subprocess
import random
import re
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

# Simpan driver di level global agar login hanya 1x
THREADS_DRIVER = None

# Path untuk Chrome profile persisten (login disimpan)
THREADS_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".threads_scraper_profile")

# WIB timezone (UTC+7)
WIB = timezone(timedelta(hours=7))

# Tanggal cutoff: 1 Januari 2025
DATE_CUTOFF = datetime(2025, 1, 1, tzinfo=timezone.utc)

# ---- Global tracking ----
_SEEN_URLS = set()


def reset_tracking():
    """Reset tracking (untuk awal run baru tanpa resume)."""
    global _SEEN_URLS
    _SEEN_URLS = set()


def load_seen_urls(urls):
    """Load URL yang sudah ada dari CSV sebelumnya (untuk resume)."""
    global _SEEN_URLS
    _SEEN_URLS.update(urls)
    print(f"    [DEDUP] {len(_SEEN_URLS)} URL sudah diketahui, akan di-skip.")


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
    """Cek apakah tanggal post >= 1 Januari 2025."""
    if not date_str:
        return True  # Jika tidak ada tanggal, tetap ambil
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt >= DATE_CUTOFF
    except Exception:
        return True


def _is_content_relevant(content, keyword):
    """Filter 2 lapis:
    1. Deteksi bahasa Indonesia (harus ada kata-kata umum Indonesia)
    2. Cek relevansi keyword (minimal 1 kata dari keyword ada di konten)
    Post harus lolos SALAH SATU dari 2 cek ini untuk disimpan."""
    if not content:
        return False
    
    content_lower = content.lower()
    
    # === LAPIS 1: Cek apakah ini bahasa Indonesia ===
    # Kata-kata yang SANGAT umum di bahasa Indonesia
    indo_common = [
        'yang', 'dan', 'dari', 'untuk', 'dengan', 'ini', 'itu',
        'ada', 'tidak', 'akan', 'bisa', 'sudah', 'juga', 'atau',
        'pada', 'karena', 'tapi', 'kalau', 'kalo', 'udah', 'gak',
        'aja', 'sih', 'dong', 'deh', 'loh', 'nih', 'banget',
        'mau', 'buat', 'sama', 'lagi', 'jadi', 'kan', 'ya',
        'aku', 'saya', 'kamu', 'dia', 'mereka', 'kita',
        'pemerintah', 'program', 'rakyat', 'Indonesia',
        'sekolah', 'desa', 'koperasi', 'makan', 'gratis',
    ]
    indo_word_count = sum(1 for w in indo_common if f' {w} ' in f' {content_lower} ')
    is_indonesian = indo_word_count >= 2  # Minimal 2 kata Indonesia umum
    
    # Jika JELAS bukan Latin (Jepang/Korea/Arab/dll), langsung tolak
    latin_chars = sum(1 for c in content if c.isascii() and c.isalpha())
    total_alpha = sum(1 for c in content if c.isalpha())
    if total_alpha > 0 and latin_chars / total_alpha < 0.3:
        return False
    
    # === LAPIS 2: Cek apakah mengandung kata dari keyword ===
    keyword_lower = keyword.lower()
    # Hapus emoji dari keyword untuk matching
    import re as _re
    keyword_clean = _re.sub(r'[^\w\s]', '', keyword_lower).strip()
    
    has_keyword = False
    if keyword_clean in content_lower:
        has_keyword = True
    else:
        words = [w for w in keyword_clean.split() if len(w) >= 3]
        if words:
            has_keyword = any(w in content_lower for w in words)
        else:
            # Keyword sangat pendek (misal "PU") — cek exact match
            has_keyword = keyword_clean in content_lower
    
    # Lolos jika:
    # 1. Ada kata dari keyword di konten (paling penting), ATAU
    # 2. Bahasa Indonesia yang kuat (>=3 kata umum) — tangkap diskusi kontekstual
    return has_keyword or (is_indonesian and indo_word_count >= 3)


def _kill_zombie_chrome():
    """Membunuh proses Chrome yang tertinggal dan mengunci profile Threads."""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            if p.info['name'] and 'chrome' in p.info['name'].lower():
                cmd = ' '.join(p.info['cmdline'] or [])
                if 'threads_scraper_profile' in cmd:
                    p.kill()
    except Exception:
        pass


def _make_chrome_options():
    """Membuat objek uc.ChromeOptions baru yang segar."""
    options = uc.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=id-ID,id,en-US,en')
    options.add_argument('--disable-features=Translate')
    # Anti-throttling: biar background tab tetap jalan lancar
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument(f'--user-data-dir={THREADS_PROFILE_DIR}')

    prefs = {
        "intl.accept_languages": "id-ID,id,en-US,en",
        "translate": {"enabled": False}
    }
    options.add_experimental_option("prefs", prefs)
    return options


def _init_driver(skip_input=False):
    """Buat driver baru dengan profile persisten."""
    global THREADS_DRIVER

    # Tutup driver lama jika ada
    if THREADS_DRIVER is not None:
        try:
            THREADS_DRIVER.quit()
        except:
            pass
        THREADS_DRIVER = None

    _kill_zombie_chrome()
    time.sleep(1)

    # Fix infinite hang when downloading chromedriver
    import socket
    socket.setdefaulttimeout(30)

    try:
        THREADS_DRIVER = uc.Chrome(options=_make_chrome_options(), version_main=156)
    except Exception as e:
        print(f"    [WARN] Gagal init uc.Chrome dengan version_main=156, mencoba tanpa: {e}")
        _kill_zombie_chrome()
        time.sleep(1)
        THREADS_DRIVER = uc.Chrome(options=_make_chrome_options())

    # Navigasi ke beranda Threads untuk cek login
    THREADS_DRIVER.get("https://www.threads.net")
    print("    [INFO] Menunggu Threads dimuat...")
    time.sleep(4)

    is_logged_in = False
    try:
        body_text = (THREADS_DRIVER.execute_script("return document.body.innerText") or "").lower()
        if 'for you' in body_text or 'untuk anda' in body_text or 'search' in body_text or 'cari' in body_text:
            is_logged_in = True
    except Exception:
        pass

    if not skip_input and not is_logged_in:
        print("\n" + "=" * 60)
        print("🚨 WAJIB CEK BROWSER THREADS 🚨")
        print("1. Jendela Chrome sudah terbuka di layar Anda.")
        print("2. Pastikan Anda SUDAH LOGIN dan melihat feed/beranda Threads.")
        print("3. Jika diminta Login Instagram, kerjakan dulu.")
        print("4. JANGAN lanjut jika layar browser masih error atau halaman login.")
        print("=" * 60 + "\n")

        try:
            input("👉 TEKAN ENTER DI SINI HANYA JIKA BROWSER SUDAH LOGIN & AMAN... ")
        except Exception:
            pass
        print("    [OK] Melanjutkan ke pencarian...")
        time.sleep(2)
    else:
        print("    [OK] Sesi Threads siap digunakan.")

    return THREADS_DRIVER


def scrape_threads(keyword, max_results=200):
    """
    Scrape Threads dengan Single-Phase extraction di tab RECENT:
    - Menggunakan tab "Recent" (bukan "Top") untuk hasil yang lebih relevan
    - Scroll + ekstraksi data langsung dari DOM
    - Filter tanggal: hanya post dari 1 Januari 2025 ke atas
    - Filter konten: skip post yang tidak relevan dengan keyword
    
    Args:
        keyword: kata kunci pencarian
        max_results: target jumlah data (default 200)
    """
    global THREADS_DRIVER, _SEEN_URLS

    print(f"    - Threads Selenium: mencari '{keyword}' (tab Recent)...")

    if THREADS_DRIVER is None:
        print("    [!] Membuka Chrome untuk Threads pertama kali...")
        _init_driver()

    # ===== NAVIGASI KE TAB "RECENT" =====
    query = urllib.parse.quote(keyword)
    # Pertama load halaman search biasa
    url = f"https://www.threads.net/search?q={query}&serp_type=default"
    
    # Navigasi dengan auto-reconnect jika Chrome crash
    for attempt in range(3):
        try:
            THREADS_DRIVER.get(url)
            break
        except (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError, OSError) as e:
            print(f"    [!] Chrome koneksi putus (attempt {attempt+1}/3): {e}")
            print("    [INFO] Merestart Chrome...")
            THREADS_DRIVER = None
            time.sleep(3)
            _init_driver()
        except Exception as e:
            err_str = str(e).lower()
            if 'connection' in err_str or 'chrome' in err_str or 'session' in err_str or 'disconnected' in err_str:
                print(f"    [!] Chrome error (attempt {attempt+1}/3): {e}")
                print("    [INFO] Merestart Chrome...")
                THREADS_DRIVER = None
                time.sleep(3)
                _init_driver()
            else:
                raise
    time.sleep(3)

    # Klik tab "Recent" / "Terbaru"
    try:
        clicked_recent = THREADS_DRIVER.execute_script("""
            const tabs = document.querySelectorAll('a, div[role="tab"], span, button');
            for (const tab of tabs) {
                const text = (tab.innerText || '').trim().toLowerCase();
                if (text === 'recent' || text === 'terbaru') {
                    tab.click();
                    return true;
                }
            }
            return false;
        """)
        if clicked_recent:
            print("    [OK] Berhasil klik tab 'Recent/Terbaru'")
            time.sleep(4)
        else:
            print("    [WARN] Tidak menemukan tab 'Recent'. Mencoba URL langsung...")
            # Fallback: coba URL parameter recent
            url = f"https://www.threads.net/search?q={query}&serp_type=recent"
            THREADS_DRIVER.get(url)
            time.sleep(4)
    except Exception as e:
        print(f"    [WARN] Gagal klik tab Recent: {e}. Mencoba URL langsung...")
        url = f"https://www.threads.net/search?q={query}&serp_type=recent"
        THREADS_DRIVER.get(url)
        time.sleep(4)

    # Tunggu konten muncul
    try:
        WebDriverWait(THREADS_DRIVER, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-pressable-container="true"], article, div[role="article"]'))
        )
    except Exception:
        try:
            body_text = (THREADS_DRIVER.execute_script("return document.body.innerText") or "").lower()

            if "no results" in body_text or "tidak ada hasil" in body_text or "tidak ditemukan" in body_text:
                print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                return []

            error_keywords = ["something went wrong", "ada yang salah", "try reloading",
                              "kesalahan teknis", "muat ulang", "rate limit",
                              "masuk untuk melanjutkan", "log in to continue"]
            if any(err in body_text for err in error_keywords):
                print("\n    [!] ERROR: Threads memblokir pencarian (Sesi expired/terkena limit).")
                THREADS_DRIVER.get("https://www.threads.net/login")
                time.sleep(3)

                print("\n" + "=" * 60)
                print("🚨 SESI THREADS KEDALUWARSA / LIMIT 🚨")
                print("1. Jendela Chrome berada di halaman Login Threads.")
                print("2. Silakan LOGIN ULANG secara manual.")
                print("3. Setelah berhasil login, pastikan pencarian manual berhasil.")
                print("4. Kembali ke sini dan tekan ENTER.")
                print("=" * 60 + "\n")

                input("👉 TEKAN ENTER JIKA SUDAH LOGIN ULANG & AMAN... ")
                print("    [INFO] Melanjutkan pencarian...")
                THREADS_DRIVER.get(url)
                time.sleep(5)
        except Exception:
            pass

    time.sleep(3)

    # Cek jumlah post di layar untuk debug
    try:
        post_count = THREADS_DRIVER.execute_script("""
            const selectors = ['div[data-pressable-container="true"]', 'article', 'div[role="article"]'];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length >= 2) return els.length;
            }
            return 0;
        """)
        print(f"    [DEBUG] Jumlah post di layar awal: {post_count}")

        if post_count == 0:
            body_text = (THREADS_DRIVER.execute_script("return document.body.innerText") or "").lower()
            if "no results" in body_text or "tidak ada hasil" in body_text:
                print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                return []

            print("    [!] Masih 0 post. Coba refresh paksa...")
            THREADS_DRIVER.refresh()
            time.sleep(7)

            # Coba klik tab Recent lagi setelah refresh
            THREADS_DRIVER.execute_script("""
                const tabs = document.querySelectorAll('a, div[role="tab"], span, button');
                for (const tab of tabs) {
                    const text = (tab.innerText || '').trim().toLowerCase();
                    if (text === 'recent' || text === 'terbaru' || text === 'utas baru') {
                        tab.click();
                        return;
                    }
                }
            """)
            time.sleep(4)

            post_count = THREADS_DRIVER.execute_script("""
                const selectors = ['div[data-pressable-container="true"]', 'article', 'div[role="article"]'];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length >= 2) return els.length;
                }
                return 0;
            """)
            print(f"    [DEBUG] Jumlah post setelah refresh: {post_count}")

            if post_count == 0:
                body_text = (THREADS_DRIVER.execute_script("return document.body.innerText") or "").lower()
                if "no results" in body_text or "tidak ada hasil" in body_text:
                    print(f"    [INFO] Pencarian kosong (Tidak ada hasil). Melewati keyword ini.")
                    return []

                print("\n" + "=" * 60)
                print("🚨 THREADS TIDAK MENAMPILKAN POST (RATE LIMIT / SESI MACET) 🚨")
                print(f"Keyword: '{keyword}' tidak memuat data di layar browser.")
                print("1. Cek jendela Chrome: blank, limit, atau perlu re-login.")
                print("2. Setelah aman, tekan ENTER untuk coba lagi.")
                print("=" * 60 + "\n")
                input("👉 TEKAN ENTER JIKA SUDAH AMAN / SIAP COBA LAGI... ")
                THREADS_DRIVER.get(url)
                time.sleep(5)
    except:
        pass

    # ========== SINGLE-PHASE: SCROLL + EXTRACT LANGSUNG ==========
    all_post_data = {}  # dictionary url/content_hash -> data
    last_height = THREADS_DRIVER.execute_script("return document.body.scrollHeight")
    no_new_count = 0
    max_no_new = 12  # Threads butuh lebih banyak patience
    date_cutoff_reached = False
    skipped_irrelevant = 0

    # JavaScript extractor — dijalankan tiap scroll
    collect_data_js = r"""
    const results = [];
    const seen = new Set();
    
    const selectors = [
        'div[data-pressable-container="true"]',
        'article',
        'div[role="article"]',
    ];
    
    let containers = [];
    for (const sel of selectors) {
        containers = document.querySelectorAll(sel);
        if (containers.length >= 2) break;
    }
    
    for (const container of containers) {
        try {
            const fullText = container.innerText.trim();
            if (!fullText || fullText.length < 20) continue;
            
            // === AUTHOR ===
            let author = '';
            const authorLink = container.querySelector('a[href*="/@"]');
            if (authorLink) {
                const href = authorLink.getAttribute('href') || '';
                const match = href.match(/@([\w_.]+)/);
                if (match) author = match[1];
                if (!author) author = authorLink.innerText.trim().replace('@', '');
            }
            // Skip akun Meta AI bot langsung
            if (author && (author.toLowerCase() === 'meta.ai' || author.toLowerCase() === 'metaai')) continue;
            
            // === URL ===
            let postUrl = '';
            const postLink = container.querySelector('a[href*="/post/"]');
            if (postLink) {
                const href = postLink.getAttribute('href') || '';
                postUrl = href.startsWith('http') ? href : 'https://www.threads.net' + href;
                postUrl = postUrl.split('?')[0];
            }
            if (postUrl && postUrl.toLowerCase().includes('/@meta.ai/')) continue;
            
            // === CONTENT ===
            // Auto-expand "more" / "selengkapnya" jika postingan panjang di Threads
            try {
                const moreBtns = container.querySelectorAll('div[role="button"], span[role="button"]');
                for (const mb of moreBtns) {
                    const mbt = (mb.innerText || '').trim().toLowerCase();
                    if (mbt === 'more' || mbt === 'selengkapnya' || mbt === '... more' || mbt === '... selengkapnya') {
                        mb.click();
                    }
                }
            } catch(e) {}

            const spans = container.querySelectorAll('span[dir="auto"]');
            let contentArr = [];
            for (const span of spans) {
                if (span.parentElement && span.parentElement.closest('span[dir="auto"]')) continue;
                
                const t = span.innerText.trim();
                if (!t) continue;
                
                const lowerT = t.toLowerCase();
                const lowerAuthor = author.toLowerCase();
                if (lowerT === lowerAuthor || lowerT === '@' + lowerAuthor) continue;
                if (lowerT === 'terjemahkan' || lowerT === 'translate' || lowerT === 'meta.ai') continue;
                if (lowerT === 'verified' || lowerT === 'terverifikasi') continue;
                if (lowerT.match(/^\d+\s*(hari|jam|menit|detik|minggu|bulan|tahun|h|m|s|w|d|y)s?$/)) continue;
                if (lowerT.match(/^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$/)) continue;
                if (/^[\d.,kKmMrRbBjJtT\s]+$/.test(t)) continue;
                if (span.closest('div[role="button"]')) continue;
                
                contentArr.push(t);
            }
            let content = contentArr.join(' ');
            if (!content || content.length < 15) continue;
            
            const contentKey = content.substring(0, 100);
            if (seen.has(contentKey)) continue;
            seen.add(contentKey);

            // === DATE ===
            let dateStr = '';
            const timeEl = container.querySelector('time');
            if (timeEl) {
                dateStr = timeEl.getAttribute('datetime') || timeEl.innerText || '';
            }

            // === ENGAGEMENT METRICS ===
            let likes = 0, replies = 0, shares = 0, reposts = 0, views = 0;
            
            const svgs = container.querySelectorAll('svg');
            for (const svg of svgs) {
                const titleNode = svg.querySelector('title');
                const titleText = (titleNode ? titleNode.textContent : svg.getAttribute('aria-label') || '').toLowerCase();
                if (!titleText) continue;
                
                let btn = svg.closest('div[role="button"]') || svg.closest('div[tabindex="0"]');
                if (!btn) continue;
                
                const rawText = btn.textContent || '';
                let numStr = rawText.toLowerCase().replace(titleText.toLowerCase(), '').trim();
                if (!numStr) continue;
                
                let num = 0;
                const match = numStr.match(/([\d.,]+)\s*(k|m|rb|jt)?/);
                if (match) {
                    let valStr = match[1];
                    if (match[2]) {
                        valStr = valStr.replace(',', '.');
                        num = parseFloat(valStr);
                        if (match[2] === 'k' || match[2] === 'rb') num *= 1000;
                        else if (match[2] === 'm' || match[2] === 'jt') num *= 1000000;
                    } else {
                        valStr = valStr.replace(/[.,]/g, '');
                        num = parseInt(valStr);
                    }
                }
                
                if (titleText.includes('suka') || titleText.includes('like') || titleText.includes('heart')) {
                    if (likes === 0 && !isNaN(num)) likes = num;
                } else if (titleText.includes('komentar') || titleText.includes('repl') || titleText.includes('balas')) {
                    if (replies === 0 && !isNaN(num)) replies = num;
                } else if (titleText.includes('repost') || titleText.includes('utas ulang') || titleText.includes('quote')) {
                    if (reposts === 0 && !isNaN(num)) reposts = num;
                } else if (titleText.includes('bagikan') || titleText.includes('share') || titleText.includes('kirim') || titleText.includes('send')) {
                    if (shares === 0 && !isNaN(num)) shares = num;
                }
            }

            results.push({
                url: postUrl,
                date: dateStr,
                text: content,
                username: author,
                likes: likes,
                views: views,
                reposts: reposts,
                shares: shares,
                replies: replies
            });
        } catch(e) {}
    }
    return results;
    """

    while len(all_post_data) < max_results:
        try:
            extracted_data = THREADS_DRIVER.execute_script(collect_data_js)
            count_before = len(all_post_data)

            for item in (extracted_data or []):
                post_url = item.get('url', '')
                username = item.get('username', '')
                content_text = item.get('text', '')
                date_str = item.get('date', '')
                
                # Wajib memiliki post_url dan username untuk integritas SNA & deduplikasi
                if not post_url or not str(post_url).strip() or not username or not str(username).strip():
                    continue

                author_clean = (username or '').lower().strip()
                # Filter Meta AI: lewati jika postingan berasal dari akun bot resmi @meta.ai (postingan user yang ngetag meta.ai tetap diambil)
                if author_clean in ['meta.ai', 'metaai', '@meta.ai'] or 'threads.net/@meta.ai' in post_url.lower():
                    continue

                # Filter tanggal: stop jika post sudah sebelum 1 Jan 2025
                if date_str and not _is_after_cutoff(date_str):
                    date_cutoff_reached = True
                    continue
                
                # Filter konten: skip post yang tidak relevan
                if not _is_content_relevant(content_text, keyword):
                    skipped_irrelevant += 1
                    continue
                
                # Deduplikasi (URL adalah Primary Key)
                dedup_key = post_url
                
                if dedup_key in all_post_data or dedup_key in _SEEN_URLS:
                    continue
                all_post_data[dedup_key] = item

            new_count = len(all_post_data) - count_before
            if new_count > 0:
                print(f"      [Scroll] {len(all_post_data)} Data terkumpul (+{new_count} baru)", end="")
                if skipped_irrelevant > 0:
                    print(f" | {skipped_irrelevant} irrelevant dibuang", end="")
                print()

            # Jika tanggal cutoff tercapai, berhenti
            if date_cutoff_reached:
                print(f"    [INFO] Tanggal post sudah melewati batas (sebelum 1 Jan 2025). Berhenti.")
                break

            if new_count == 0:
                no_new_count += 1
                if no_new_count >= max_no_new:
                    print(f"    [INFO] Mentok maksimal! {max_no_new}x scroll tanpa data baru. Berhenti.")
                    break
            else:
                no_new_count = 0

            if len(all_post_data) >= max_results:
                break

            THREADS_DRIVER.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2.5, 4.5))

            # Cek error di tengah scroll
            body_text = (THREADS_DRIVER.execute_script("return document.body.innerText") or "").lower()
            error_keywords = ["something went wrong", "ada yang salah", "try reloading",
                              "kesalahan teknis", "muat ulang", "rate limit",
                              "masuk untuk melanjutkan"]
            if len(body_text) < 500 and any(err in body_text for err in error_keywords):
                print("\n    [!] ERROR DI TENGAH SCROLL: Threads memblokir pencarian.")
                THREADS_DRIVER.get("https://www.threads.net/login")
                time.sleep(3)

                print("\n" + "=" * 60)
                print("🚨 SESI THREADS KEDALUWARSA / LIMIT DI TENGAH JALAN 🚨")
                print("1. Silakan LOGIN ULANG (pakai akun lain jika limit).")
                print("2. Jika pencarian manual berhasil, kembali ke sini dan tekan ENTER.")
                print("=" * 60 + "\n")

                input("👉 TEKAN ENTER JIKA SUDAH LOGIN ULANG & AMAN... ")

                print("    [INFO] Melanjutkan pencarian (scroll ulang dari atas)...")
                THREADS_DRIVER.get(url)
                time.sleep(5)
                # Klik tab Recent lagi setelah re-login
                THREADS_DRIVER.execute_script("""
                    const tabs = document.querySelectorAll('a, div[role="tab"], span, button');
                    for (const tab of tabs) {
                        const text = (tab.innerText || '').trim().toLowerCase();
                        if (text === 'recent' || text === 'terbaru' || text === 'utas baru') {
                            tab.click();
                            return;
                        }
                    }
                """)
                time.sleep(4)
                continue

            new_height = THREADS_DRIVER.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                time.sleep(2)
                new_height = THREADS_DRIVER.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_new_count += 1
            last_height = new_height

        except KeyboardInterrupt:
            print("\n    [!] Jeda / Ctrl+C terdeteksi. Menyimpan data yang sudah terkumpul sejauh ini...")
            break
        except Exception as e:
            print(f"    [WARN] Error saat scroll: {e}")
            break

    print(f"    [INFO] Selesai. Total {len(all_post_data)} data post berhasil diekstrak.")
    if skipped_irrelevant > 0:
        print(f"    [INFO] {skipped_irrelevant} post tidak relevan dibuang.")

    # Format hasil akhir
    final_data = []
    for item in all_post_data.values():
        date_str = item.get('date', '')
        content = item.get('text', '')
        # Clean single-line
        clean_text = content.replace('\n', ' ').replace('\r', ' ')
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        # Hapus sisa UI text
        clean_text = re.sub(r'(?:\s*\d+\s*/\s*\d+[^a-zA-Z0-9]*|\s*Terjemahkan\s*|\s*meta\.ai\s*)$', '', clean_text, flags=re.IGNORECASE).strip()

        if len(clean_text) < 15:
            continue

        post_url = item.get('url', '')
        author = item.get('username', '') or 'Threads_User'

        final_data.append({
            'platform': 'Threads',
            'keyword': keyword,
            'url': post_url,
            'handle': f"@{author}" if author != 'Threads_User' else '',
            'content': clean_text[:500],
            'created_at': _to_wib(date_str),
            'likes': int(item.get('likes', 0)),
            'comments': int(item.get('replies', 0)),
            'reposts': int(item.get('reposts', 0)),
            'shares': int(item.get('shares', 0)),
            'views': int(item.get('views', 0)),
            'scraped_at': datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB',
        })
        if post_url:
            _SEEN_URLS.add(post_url)

    print(f"    [OK] {len(final_data)} data post terfilter & bersih.")
    return final_data


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("[TEST] Memulai test scrape Threads (Selenium)...")
    data = scrape_threads("Kementerian Pekerjaan Umum", max_results=5)
    print(f"Berhasil ambil {len(data)} data")
    for d in data:
        print(f"  - Likes: {d['likes']}, Comments: {d['comments']}, Handle: {d['handle']}")
        print(f"    Content: {d['content'][:80]}...")
    if THREADS_DRIVER:
        THREADS_DRIVER.quit()
