"""
================================================================================
🚀 ENRICH FACEBOOK CREATED_AT RUNNER (SELENIUM UNDETECTED)
================================================================================
Membuka satu per satu link postingan Facebook yang ada di:
  d:\\Project_Streamlit\\IndoBERT_SNA_MT_PP\\ScrapeData\\scraped_Facebook_Only.csv
Untuk mengekstrak tanggal asli postingan (created_at) dengan regulasi:
  1. Engine Undetected ChromeDriver dengan profil persisten (~/.facebook_scraper_profile)
  2. Dialog & Popup Auto-Dismisser (OK / Tutup / Temporarily Blocked dialog)
  3. Rate-Limit / Block Guardian & graceful relogin via flag --relogin
  4. Human Jitter Delay (acak 2.0 - 3.5s) agar aman dari deteksi Meta
  5. Multi-Strategy Date Extraction:
     - Regex JSON GraphQL / Relay store ("creation_time", "publish_time", "created_time")
     - DOM inspection (abbr[data-utime], time[datetime], a[aria-label], header links)
     - Smart Indonesian & English relative/absolute date parser
  6. Auto-Resume: Melewati URL yang sudah berhasil memiliki created_at
  7. Real-Time Checkpointing: Langsung menyimpan perubahan ke CSV berkala & saat Ctrl+C
================================================================================
"""

import os
import sys
import re
import time
import shutil
import random
import argparse
from datetime import datetime, timezone, timedelta
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

WIB = timezone(timedelta(hours=7))

# Direktori profil Chrome persisten (sama persis dengan cobaAPI cell_09_facebook)
FB_PROFILE_DIR = os.path.join(os.path.expanduser('~'), '.facebook_scraper_profile')
os.makedirs(FB_PROFILE_DIR, exist_ok=True)

# Path file CSV Facebook
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'ScrapeData')
CSV_PATH = os.path.join(DATA_DIR, 'scraped_Facebook_Only.csv')

# Kamus Nama Bulan untuk Parser Teks Tanggal
MONTH_MAP = {
    'januari': 1, 'jan': 1, 'january': 1,
    'februari': 2, 'feb': 2, 'february': 2,
    'maret': 3, 'mar': 3, 'march': 3,
    'april': 4, 'apr': 4,
    'mei': 5, 'may': 5,
    'juni': 6, 'jun': 6, 'june': 6,
    'juli': 7, 'jul': 7, 'july': 7,
    'agustus': 8, 'agu': 8, 'agt': 8, 'aug': 8, 'august': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'oktober': 10, 'okt': 10, 'oct': 10, 'october': 10,
    'november': 11, 'nov': 11,
    'desember': 12, 'des': 12, 'dec': 12, 'december': 12
}

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
except ImportError:
    print("[ERROR] Library 'undetected-chromedriver' atau 'selenium' belum terinstall!")
    print("        Silakan install: pip install undetected-chromedriver selenium")
    sys.exit(1)

FB_DRIVER = None


# ==============================================================================
# 1. PARSER TANGGAL & TIMESTAMP
# ==============================================================================

def parse_epoch_to_wib(epoch):
    """Konversi epoch timestamp detik atau milidetik ke string 'YYYY-MM-DD HH:MM:SS WIB'."""
    try:
        val = int(epoch)
        # Jika dalam milidetik (13 digit)
        if val > 100000000000:
            val = val // 1000
        # Rentang logis tahun 2020 s/d 2030
        if 1577836800 <= val <= 1893456000:
            dt = datetime.fromtimestamp(val, tz=WIB)
            return dt.strftime('%Y-%m-%d %H:%M:%S WIB')
    except Exception:
        pass
    return ""


def parse_facebook_date_str(text, reference_dt=None):
    """
    Mengurai berbagai variasi format teks tanggal dan waktu Facebook
    (relatif bahasa Indonesia & Inggris, serta absolut format tanggal).
    """
    if not text:
        return ""
    if reference_dt is None:
        reference_dt = datetime.now(WIB)
    
    t = str(text).lower().strip()
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t)

    # A. Cek langsung angka epoch 10 digit (detik) atau 13 digit (milidetik)
    if t.isdigit() and (len(t) == 10 or len(t) == 13):
        res = parse_epoch_to_wib(t)
        if res:
            return res

    # B. Cek ISO format
    if 't' in t or re.match(r'^\d{4}-\d{2}-\d{2}', t):
        try:
            iso_clean = t.replace('z', '+00:00').upper()
            dt = datetime.fromisoformat(iso_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=WIB)
            else:
                dt = dt.astimezone(WIB)
            return dt.strftime('%Y-%m-%d %H:%M:%S WIB')
        except Exception:
            pass

    # C. Format Day Month Year (ID & EN): '14 Oktober 2024 pukul 10:35' / '5 Maret pukul 08.15'
    pattern_dmy = r'\b(\d{1,2})\s+([a-zA-Z]+)(?:[,\s]+(\d{4}))?(?:.*?(\d{1,2})[:\.](\d{2}))?'
    m_dmy = re.search(pattern_dmy, t)
    if m_dmy:
        month_name = m_dmy.group(2).lower()
        if month_name in MONTH_MAP:
            day = int(m_dmy.group(1))
            month = MONTH_MAP[month_name]
            year = int(m_dmy.group(3)) if m_dmy.group(3) else reference_dt.year
            hour = int(m_dmy.group(4)) if m_dmy.group(4) else 12
            minute = int(m_dmy.group(5)) if m_dmy.group(5) else 0
            if 'pm' in t and hour < 12: hour += 12
            if 'am' in t and hour == 12: hour = 0
            try:
                dt = datetime(year, month, day, hour, minute, 0, tzinfo=WIB)
                return dt.strftime('%Y-%m-%d %H:%M:%S WIB')
            except Exception:
                pass

    # D. Format Month Day Year (EN): 'February 15, 2025 at 4:30 PM' / 'Oct 24, 2024'
    pattern_mdy = r'\b([a-zA-Z]+)\s+(\d{1,2})(?:[,\s]+(\d{4}))?(?:.*?(\d{1,2})[:\.](\d{2}))?'
    m_mdy = re.search(pattern_mdy, t)
    if m_mdy:
        month_name = m_mdy.group(1).lower()
        if month_name in MONTH_MAP:
            month = MONTH_MAP[month_name]
            day = int(m_mdy.group(2))
            year = int(m_mdy.group(3)) if m_mdy.group(3) else reference_dt.year
            hour = int(m_mdy.group(4)) if m_mdy.group(4) else 12
            minute = int(m_mdy.group(5)) if m_mdy.group(5) else 0
            if 'pm' in t and hour < 12: hour += 12
            if 'am' in t and hour == 12: hour = 0
            try:
                dt = datetime(year, month, day, hour, minute, 0, tzinfo=WIB)
                return dt.strftime('%Y-%m-%d %H:%M:%S WIB')
            except Exception:
                pass

    # E. Format Relatif 'Kemarin pukul 14:30' / 'Yesterday at 2:30 pm'
    if 'kemarin' in t or 'yesterday' in t:
        dt = reference_dt - timedelta(days=1)
        m_time = re.search(r'(\d{1,2})[:\.](\d{2})', t)
        if m_time:
            h, mi = int(m_time.group(1)), int(m_time.group(2))
            if 'pm' in t and h < 12: h += 12
            if 'am' in t and h == 12: h = 0
            dt = dt.replace(hour=h, minute=mi, second=0)
        return dt.strftime('%Y-%m-%d %H:%M:%S WIB')

    # F. Relatif Jam: X jam / X hrs / Xh
    m_h = re.search(r'\b(\d+)\s*(?:jam|hrs?|hours?)\b', t) or re.search(r'\b(\d+)h\b', t)
    if m_h:
        hours = int(m_h.group(1))
        dt = reference_dt - timedelta(hours=hours)
        return dt.strftime('%Y-%m-%d %H:%M:%S WIB')

    # G. Relatif Menit: X menit / X mins / Xm
    m_m = re.search(r'\b(\d+)\s*(?:menit|mins?|minutes?)\b', t) or re.search(r'\b(\d+)m\b', t)
    if m_m:
        mins = int(m_m.group(1))
        dt = reference_dt - timedelta(minutes=mins)
        return dt.strftime('%Y-%m-%d %H:%M:%S WIB')

    # H. Relatif Hari: X hari / X days / Xd
    m_d = re.search(r'\b(\d+)\s*(?:hari|days?)\b', t) or re.search(r'\b(\d+)d\b', t)
    if m_d:
        days = int(m_d.group(1))
        dt = reference_dt - timedelta(days=days)
        return dt.strftime('%Y-%m-%d %H:%M:%S WIB')

    return ""


# ==============================================================================
# 2. BROWSER CONTROLLER & GUARDIAN (REGULASI COBAAPI)
# ==============================================================================

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
    options.add_argument("--disable-notifications")
    options.add_argument('--lang=id-ID,id,en-US,en')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=CalculateNativeWinOcclusion')
    options.add_argument(f'--user-data-dir={FB_PROFILE_DIR}')
    return options


def _init_driver(skip_input=False):
    """Inisialisasi Chrome dengan profil persisten dan deteksi login aktif."""
    global FB_DRIVER

    if FB_DRIVER is not None:
        try:
            FB_DRIVER.quit()
        except Exception:
            pass
        FB_DRIVER = None

    major_v = _get_chrome_major_version()
    driver_started = False

    # 1. Coba dengan versi utama Chrome yang terpasang di sistem
    if major_v:
        try:
            FB_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=major_v)
            driver_started = True
        except Exception as e:
            print(f"    [WARN] Inisialisasi Chrome dengan version_main={major_v} gagal: {e}")
            time.sleep(1)

    # 2. Coba auto-detect bawaan uc.Chrome jika langkah 1 gagal
    if not driver_started:
        try:
            FB_DRIVER = uc.Chrome(options=_build_chrome_options())
            driver_started = True
        except Exception as e:
            print(f"    [WARN] Inisialisasi auto-detect Chrome gagal: {e}")
            time.sleep(1)

    # 3. Fallback toleransi versi sebelumnya jika masih belum terbuka
    if not driver_started and major_v:
        for fallback_v in [major_v - 1, major_v - 2]:
            try:
                FB_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=fallback_v)
                driver_started = True
                break
            except Exception:
                pass

    if not driver_started or FB_DRIVER is None:
        raise RuntimeError("Gagal membuka Chrome Selenium. Pastikan tidak ada proses Chrome background yang mengunci profil.")

    FB_DRIVER.get("https://www.facebook.com/")
    print("    [INFO] Membuka Facebook di Chrome...")
    time.sleep(3)

    is_logged_in = False
    try:
        is_logged_in = FB_DRIVER.execute_script("""
            return !document.querySelector('input[name="email"]') && 
                   !document.querySelector('button[name="login"]') &&
                   (!!document.querySelector('div[role="navigation"]') || !!document.querySelector('svg[aria-label="Your profile"]'));
        """)
    except Exception:
        pass

    if not is_logged_in and not skip_input:
        print("\n" + "=" * 65)
        print("🔐 SILAKAN LOGIN KE AKUN FACEBOOK ANDA DI BROWSER 🔐")
        print("1. Jendela Chrome sudah terbuka di https://www.facebook.com/")
        print("2. Silakan login ke akun Facebook Anda (Akun cadangan/utama).")
        print("3. Selesaikan 2FA / verifikasi jika diminta.")
        print("4. Pastikan Anda sudah masuk ke Beranda Facebook.")
        print("=" * 65 + "\n")
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            try:
                input("👉 TEKAN ENTER DI SINI JIKA SUDAH BERHASIL MASUK KE BERANDA FB... ")
            except (EOFError, KeyboardInterrupt):
                pass
            print("    [OK] Melanjutkan ke proses ekstraksi link...")
            time.sleep(2)
        else:
            print("    [INFO] Menunggu Anda login di browser (maksimal 120 detik)...")
            for _ in range(40):
                time.sleep(3)
                try:
                    check_in = FB_DRIVER.execute_script("""
                        return !document.querySelector('input[name="email"]') && 
                               !document.querySelector('button[name="login"]') &&
                               (!!document.querySelector('div[role="navigation"]') || !!document.querySelector('svg[aria-label="Your profile"]'));
                    """)
                    if check_in:
                        print("    [OK] Sesi login Facebook aktif ditemukan!")
                        break
                except Exception:
                    pass
    elif is_logged_in:
        print("    [OK] Sesi login Facebook aktif ditemukan!")

    return FB_DRIVER


def _check_facebook_blocked(driver):
    """Mendeteksi apakah halaman Facebook menampilkan pembatasan / Temporarily Blocked."""
    if driver is None:
        return False
    try:
        check_js = """
        let texts = [];
        let dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"], div[aria-modal="true"]');
        dialogs.forEach(d => { if (d.innerText) texts.push(d.innerText.toLowerCase()); });
        if (document.body && document.body.innerText) {
            texts.push(document.body.innerText.toLowerCase());
        }
        let full = texts.join(' ');
        let blockPhrases = [
            'temporarily blocked', 'misusing this feature', 'going too fast',
            'you’ve been temporarily blocked', "you've been temporarily blocked",
            'you’re temporarily blocked', "you're temporarily blocked",
            'diblokir sementara', 'menyalahgunakan fitur', 'terlalu cepat',
            'kami membatasi', 'tindakan ini diblokir', 'coba lagi nanti', 'try again later'
        ];
        return blockPhrases.some(phrase => full.includes(phrase));
        """
        return bool(driver.execute_script(check_js))
    except Exception:
        return False


def _dismiss_facebook_popups(driver):
    """Menutup modal dialog pop-up yang menghalangi konten."""
    if driver is None:
        return
    try:
        dismiss_js = """
        let btns = document.querySelectorAll(
            'div[role="dialog"] div[role="button"], div[role="dialog"] button, ' +
            'div[role="alertdialog"] div[role="button"], div[role="alertdialog"] button, ' +
            'div[aria-modal="true"] div[role="button"], div[aria-modal="true"] button'
        );
        btns.forEach(btn => {
            let t = (btn.innerText || '').trim().toLowerCase();
            let aria = (btn.getAttribute('aria-label') || '').trim().toLowerCase();
            if (t === 'ok' || t === 'tutup' || t === 'close' || 
                aria === 'ok' || aria.includes('tutup') || aria.includes('close') || aria === 'oke') {
                try { btn.click(); } catch(e) {}
            }
        });

        let dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"], div[aria-modal="true"]');
        dialogs.forEach(d => {
            let txt = (d.innerText || '').toLowerCase();
            if (txt.includes('temporarily blocked') || txt.includes('diblokir sementara') || 
                txt.includes('misusing this feature') || txt.includes('terlalu cepat') || txt.includes('going too fast')) {
                try { d.remove(); } catch(e) {}
            }
        });
        """
        driver.execute_script(dismiss_js)
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
    except Exception:
        pass


def _force_relogin():
    """Reset session/cookies lama dan pandu login akun baru saat kena rate-limit parah."""
    global FB_DRIVER
    print("\n" + "=" * 65)
    print("🚨 DETEKSI RATE LIMIT / BLOKIR SEMENTARA FACEBOOK 🚨")
    print("Mereset sesi browser agar Anda dapat login dengan akun Facebook cadangan...")
    print("=" * 65)

    if FB_DRIVER is not None:
        try:
            FB_DRIVER.quit()
        except Exception:
            pass
        FB_DRIVER = None

    time.sleep(2)
    if os.path.exists(FB_PROFILE_DIR):
        try:
            shutil.rmtree(FB_PROFILE_DIR, ignore_errors=True)
            print("    [OK] Profil & cookies lama berhasil dibersihkan.")
        except Exception as e:
            print(f"    [WARN] Gagal membersihkan folder profile: {e}")

    _init_driver(skip_input=False)
    print("    [OK] Login akun baru berhasil! Melanjutkan proses scraping...\n")


# ==============================================================================
# 3. EXTRACTION ENGINE: MEMBUKA LINK & MENGAMBIL CREATED_AT
# ==============================================================================

def extract_created_at_from_page(driver, url, reference_dt=None):
    """
    Membuka 1 URL Facebook dan mengekstrak tanggal postingan menggunakan
    multi-strategy extraction (JSON source, DOM attributes, dan aria-labels).
    """
    if not url or not url.startswith('http') or 'facebook.com' not in url:
        return ""

    try:
        driver.get(url)
    except Exception as e:
        print(f"        [ERR] Gagal load URL: {e}")
        return ""

    # Tunggu sebentar agar elemen DOM dan script ter-render
    time.sleep(random.uniform(1.8, 2.5))
    _dismiss_facebook_popups(driver)

    # Deteksi rate-limit
    if _check_facebook_blocked(driver):
        print("        [WARN] Terdeteksi pesan pembatasan sementara / rate limit!")
        return "BLOCKED"

    # ---------------------------------------------------------
    # STRATEGI 1: Regex pada Page Source (Script Tags & JSON)
    # Ini metode paling presisi karena menangkap epoch time asli
    # ---------------------------------------------------------
    try:
        html_src = driver.page_source
        
        # Cari pola epoch creation_time / publish_time (detik 10 digit atau milidetik 13 digit)
        epoch_patterns = [
            r'"creation_time":\s*(\d{10,13})\b',
            r'"publish_time":\s*(\d{10,13})\b',
            r'"created_time":\s*(\d{10,13})\b',
            r'"story_creation_time":\s*(\d{10,13})\b',
            r'"published_time":\s*(\d{10,13})\b',
            r'"post_timestamp":\s*(\d{10,13})\b',
            r'"video_publish_date":\s*(\d{10,13})\b',
            r'"upload_date":\s*(\d{10,13})\b',
            r'data-utime="(\d{10,13})"',
            r'data-timestamp="(\d{10,13})"'
        ]
        
        for pat in epoch_patterns:
            matches = re.findall(pat, html_src)
            for m in matches:
                res = parse_epoch_to_wib(m)
                if res:
                    return res

        # Cari ISO datetime dalam meta tags
        meta_matches = re.findall(r'<meta[^>]+(?:article:published_time|og:updated_time)[^>]+content="([^"]+)"', html_src, re.IGNORECASE)
        for m in meta_matches:
            res = parse_facebook_date_str(m, reference_dt=reference_dt)
            if res:
                return res
    except Exception:
        pass

    # ---------------------------------------------------------
    # STRATEGI 2: DOM Injection via JavaScript
    # Mencari elemen abbr, time, a[aria-label], dan link timestamp
    # ---------------------------------------------------------
    extract_dom_js = """
    let candidates = [];
    
    // 1. Cek elemen abbr dengan data-utime
    document.querySelectorAll('abbr[data-utime]').forEach(el => {
        let ut = el.getAttribute('data-utime');
        if (ut) candidates.push(ut);
    });

    // 2. Cek elemen time
    document.querySelectorAll('time').forEach(el => {
        let dt = el.getAttribute('datetime');
        if (dt) candidates.push(dt);
        if (el.innerText) candidates.push(el.innerText);
    });

    // 3. Cek aria-label & teks pada permalink/header links
    let links = Array.from(document.querySelectorAll('a[role="link"], a[href*="/posts/"], a[href*="/permalink/"], a[href*="fbid="], a[href*="/photo"], a[href*="/videos/"], a[href*="/reel/"], span[dir="auto"] a, h2 ~ div a, h3 ~ div a, h4 ~ div a, div[role="article"] a'));
    links.forEach(a => {
        let aria = a.getAttribute('aria-label');
        if (aria && aria.length > 3 && aria.length < 80) {
            candidates.push(aria);
        }
        let title = a.getAttribute('title');
        if (title && title.length > 3 && title.length < 80) {
            candidates.push(title);
        }
        let txt = (a.innerText || '').trim();
        if (txt && txt.length > 1 && txt.length < 50 && !/^(like|suka|comment|komentar|share|bagikan|follow|ikuti)$/i.test(txt)) {
            candidates.push(txt);
        }
    });

    // 4. Cek span teks langsung di bawah nama author / header pos
    document.querySelectorAll('div[role="article"] span, div[data-ad-preview="message"] span, div[role="main"] span').forEach(s => {
        let t = (s.innerText || '').trim();
        if (t && /\\b(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|kemarin|yesterday|jam|menit|hari|ago|mins|hrs)\\b/i.test(t)) {
            candidates.push(t);
        }
    });

    return candidates.slice(0, 30);
    """
    try:
        dom_candidates = driver.execute_script(extract_dom_js) or []
        for cand in dom_candidates:
            res = parse_facebook_date_str(cand, reference_dt=reference_dt)
            if res:
                return res
    except Exception:
        pass

    return ""


# ==============================================================================
# 4. MAIN ENRICHMENT PIPELINE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Enrich Facebook created_at via Selenium Undetected")
    parser.add_argument('--relogin', action='store_true', help="Force reset profil Chrome dan relogin akun baru")
    parser.add_argument('--limit', type=int, default=0, help="Batasi jumlah link yang akan diproses (0 = semua)")
    parser.add_argument('--save-every', type=int, default=5, help="Simpan ke CSV setiap N link (default 5)")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 MEMULAI PROSES SCRAPING CREATED_AT FACEBOOK SATU PER SATU")
    print(f"📁 Target File : {CSV_PATH}")
    print("📋 Regulasi    : Sesuai cobaAPI (undetected-chromedriver + auto-resume)")
    print("=" * 70)

    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] File {CSV_PATH} tidak ditemukan!")
        sys.exit(1)

    # 1. Baca dataset
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(CSV_PATH)

    print(f"[INFO] Total data di CSV: {len(df):,} baris")

    # 2. Backup otomatis sebelum modifikasi
    backup_path = os.path.join(DATA_DIR, f"scraped_Facebook_Only_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy2(CSV_PATH, backup_path)
    print(f"[BACKUP] File cadangan otomatis dibuat: {os.path.basename(backup_path)}")

    # 3. Pastikan kolom created_at ada
    if 'created_at' not in df.columns:
        # Masukkan created_at tepat sebelum keyword / scraped_at
        cols = list(df.columns)
        if 'keyword' in cols:
            idx = cols.index('keyword')
            cols.insert(idx, 'created_at')
        else:
            cols.append('created_at')
        df['created_at'] = ""
        df = df[cols]

    # 4. Identifikasi baris yang perlu di-scrape (Auto-Resume)
    mask_needs_date = df['created_at'].isna() | (df['created_at'].astype(str).str.strip() == '') | (df['created_at'].astype(str).str.lower() == 'nan')
    indices_to_process = df[mask_needs_date].index.tolist()

    already_done = len(df) - len(indices_to_process)
    print(f"[STATUS] Data yang SUDAH memiliki created_at : {already_done:,} baris (Akan dilewati / Skip)")
    print(f"[STATUS] Data yang PERLU di-scrape created_at: {len(indices_to_process):,} baris")

    if len(indices_to_process) == 0:
        print("\n🎉 SEMUA DATA FACEBOOK SUDAH MEMILIKI CREATED_AT LENGKAP!")
        return

    if args.limit > 0:
        indices_to_process = indices_to_process[:args.limit]
        print(f"[LIMIT] Dibatasi hanya memproses {len(indices_to_process)} baris.")

    # 5. Opsi Relogin
    if args.relogin:
        _force_relogin()
    else:
        _init_driver(skip_input=False)

    # Helper untuk simpan data dengan aman
    def save_checkpoint(reason="Checkpoint"):
        try:
            # Standarisasi urutan kolom
            cols_order = ['platform', 'topic', 'content', 'author', 'url', 'likes', 'comments', 'shares', 'created_at', 'keyword', 'scraped_at']
            ordered = [c for c in cols_order if c in df.columns] + [c for c in df.columns if c not in cols_order]
            df[ordered].to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
            filled = df['created_at'].notna() & (df['created_at'].str.strip() != '')
            print(f"        💾 [{reason}] Tersimpan! Total terisi created_at: {filled.sum():,}/{len(df):,}")
        except Exception as e:
            print(f"        [ERR] Gagal menyimpan checkpoint: {e}")

    success_count = 0
    fail_count = 0
    consecutive_blocked = 0

    print("\n" + "=" * 70)
    print("▶ MEMULAI EKSTRAKSI TANGGAL PER URL...")
    print("  (Tekan Ctrl+C kapan saja untuk berhenti aman — data otomatis tersimpan)")
    print("=" * 70 + "\n")

    try:
        for count, idx in enumerate(indices_to_process, 1):
            row = df.loc[idx]
            url = str(row.get('url', '')).strip()
            topic = str(row.get('topic', ''))
            author = str(row.get('author', ''))[:20]
            scraped_at_raw = str(row.get('scraped_at', ''))

            # Parse scraped_at sebagai referensi waktu relatif jika ada
            ref_dt = None
            if scraped_at_raw:
                try:
                    ref_dt = datetime.strptime(scraped_at_raw.replace(' WIB', ''), '%Y-%m-%d %H:%M:%S').replace(tzinfo=WIB)
                except Exception:
                    ref_dt = None

            print(f"[{count:,}/{len(indices_to_process):,}] Row #{idx} [{topic}] {author}:")
            print(f"    URL: {url[:75]}...")

            created_at = extract_created_at_from_page(FB_DRIVER, url, reference_dt=ref_dt)

            if created_at == "BLOCKED":
                consecutive_blocked += 1
                if consecutive_blocked >= 3:
                    print("\n🚨 TERDETEKSI 3X BLOKIR/RATE LIMIT BERTURUT-TURUT!")
                    print("   Menyimpan progress yang ada dan meminta ganti sesi akun...")
                    save_checkpoint("Rate-Limit Guard")
                    _force_relogin()
                    consecutive_blocked = 0
                else:
                    time.sleep(5)
                continue
            else:
                consecutive_blocked = 0

            if created_at:
                df.at[idx, 'created_at'] = created_at
                success_count += 1
                print(f"    ✅ Tanggal ditemukan: {created_at}")
            else:
                # Kalo emang gadapet, KOSONGIN AJA (tanpa fallback!)
                df.at[idx, 'created_at'] = ""
                fail_count += 1
                print(f"    ❌ Tanggal tidak ditemukan di DOM/JSON -> Dikosongkan (Sesuai instruksi)")

            # Auto-save berkala
            if count % args.save_every == 0:
                save_checkpoint(f"Batch #{count}")

            # Jitter delay acak agar tidak memicu deteksi Meta
            delay = random.uniform(2.0, 3.5)
            time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n⚠️ DIHENTIKAN OLEH USER (Ctrl+C) — Menyimpan semua progress...")
        save_checkpoint("User Interrupted")
        print("💡 Anda dapat menjalankan ulang script ini kapan saja untuk melanjutkan.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error tidak terduga dalam loop scraping: {e}")
        save_checkpoint("Error Recovery")

    # Simpan hasil akhir
    save_checkpoint("Selesai")

    print("\n" + "=" * 70)
    print("🎉 PROSES SELESAI!")
    print(f"   - Sukses ambil tanggal asli : {success_count:,}")
    print(f"   - Fallback / Tidak terbaca  : {fail_count:,}")
    print(f"   - File tersimpan di        : {CSV_PATH}")
    print("=" * 70)

    if FB_DRIVER:
        try:
            FB_DRIVER.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()
