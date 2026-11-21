"""
================================================================================
🎯 CLI SCRAPER THREADS INTERAKTIF & FLEKSIBEL (KEMEN PU)
Engine: omkarcloud/threads-scraper (GraphQL API + TLS Impersonation via curl_cffi)
================================================================================
Cara Penggunaan:
  1. Jalankan interaktif (tanya keyword & tanggal):
     python scrape_threads.py

  2. Scrape keyword spesifik:
     python scrape_threads.py "Kementerian PU"

  3. Scrape beberapa keyword sekaligus:
     python scrape_threads.py "PUPR" "Dody Hanggodo" "Diana Kusumastuti"

  4. Tentukan rentang tanggal custom:
     python scrape_threads.py "Kemen PU" --since 2026-11-05 --until 2026-11-20

  5. Scrape profil akun resmi Threads:
     python scrape_threads.py @kementerianpu @dpupr.denpasarkota

  6. Jalankan seluruh keyword proyek default Kemen PU:
     python scrape_threads.py --all
================================================================================
"""

import os
import sys
import argparse
import time
from datetime import datetime, timezone, timedelta
import pandas as pd

# Fix console encoding Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CELLS_DIR = os.path.join(BASE_DIR, 'colab_cells')
TS_PATH = os.path.join(CELLS_DIR, 'threads_scraper')
SCRAPE_DIR = os.path.join(BASE_DIR, 'ScrapeData')
os.makedirs(SCRAPE_DIR, exist_ok=True)

sys.path.insert(0, TS_PATH)
sys.path.insert(0, CELLS_DIR)

try:
    from threads import discovery, users, refs
except ImportError as e:
    print(f"❌ Error mengimpor threads engine: {e}")
    sys.exit(1)

try:
    from cell_02_config import detect_topic, TOPICS
    # 12 Keyword Resmi Persis dari cell_02_config.py
    OFFICIAL_12_KEYWORDS = [kw for kws in TOPICS.values() for kw in kws]
except ImportError:
    detect_topic = None
    OFFICIAL_12_KEYWORDS = [
        # Kementerian_PU (6)
        "Kementerian Pekerjaan Umum",
        "Kementerian Pekerjaan Umum Republik Indonesia",
        "Kementerian PU",
        "Kementerian PU RI",
        "Kemen PU",
        "Kemen PU RI",
        # Menteri_PU (6)
        "Menteri Pekerjaan Umum",
        "Menteri Pekerjaan Umum Dody Hanggodo",
        "Menteri PU",
        "Menteri PU Dody Hanggodo",
        "Menteri Dody Hanggodo",
        "Dody Hanggodo",
    ]

# Variasi Tambahan Populer (Singkatan Netizen & Akun Dinas Resmi)
EXPANDED_EXTRAS = [
    "KemenPU",
    "PUPR",
    "kemenpupr",
    "dinas pupr",
    "proyek pupr",
    "Diana Kusumastuti",
    "Wamen PU",
    "@kementerianpu",
    "@dpupr.denpasarkota",
    "@pu_konstruksi_bp2jksulsel",
    "@pu_konstruksi_bp2jk_sulbar",
    "@pu_prasaranastrategis_sulsel",
    "@pu_sda_bhgk",
    "@pu_jalan_dkijabar"
]

WIB = timezone(timedelta(hours=7))
DEFAULT_SINCE = "2026-11-15"
DEFAULT_UNTIL = "2026-11-21"
CSV_PATH = os.path.join(SCRAPE_DIR, "scraped_Threads_Only.csv")

# Default adalah 12 Keyword Resmi Persis dari cell_02_config.py
DEFAULT_PROJECT_KEYWORDS = OFFICIAL_12_KEYWORDS

def load_existing_dataset(filepath):
    if not os.path.exists(filepath):
        return [], set()
    try:
        df = pd.read_csv(filepath, low_memory=False)
        seen = set(df['url'].dropna().unique()) if 'url' in df.columns else set()
        return df.to_dict('records'), seen
    except Exception as e:
        print(f"⚠️ Peringatan saat membaca CSV lama: {e}")
        return [], set()

def save_to_csv(records, filepath):
    cols_order = [
        'platform', 'keyword', 'url', 'handle', 'content',
        'created_at', 'likes', 'comments', 'reposts', 'shares',
        'views', 'scraped_at', 'topic'
    ]
    df = pd.DataFrame(records)
    if 'url' in df.columns and len(df) > 0:
        mask_url = df['url'].notna() & (df['url'] != '')
        df_url = df[mask_url].drop_duplicates(subset=['url'], keep='first')
        df_no = df[~mask_url]
        df = pd.concat([df_url, df_no], ignore_index=True)
    
    # Sanitasi kolom
    ordered = [c for c in cols_order if c in df.columns] + [c for c in df.columns if c not in cols_order]
    df = df[ordered]
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    return len(df)

def run_scraper(keywords, since_str, until_str):
    print("\n" + "=" * 70)
    print("🚀 MEMULAI SCRAPING THREADS BERBASIS GRAPHQL API (CURL_CFFI)")
    print("=" * 70)
    print(f"📅 Rentang Tanggal Target : {since_str} s.d. {until_str}")
    print(f"🔍 Jumlah Query/Akun      : {len(keywords)} item")
    print(f"📁 File Database Output   : {CSV_PATH}")
    print("=" * 70)

    all_records, seen_urls = load_existing_dataset(CSV_PATH)
    print(f"📦 Data tersimpan sebelumnya : {len(all_records):,} baris ({len(seen_urls):,} URL unik)\n")

    total_added_session = 0

    for idx, kw in enumerate(keywords, 1):
        kw_clean = kw.strip()
        if not kw_clean:
            continue

        is_user = kw_clean.startswith('@')
        target_name = f"Akun '{kw_clean}'" if is_user else f"Keyword '{kw_clean}'"
        print("-" * 70)
        print(f"[{idx:02d}/{len(keywords):02d}] 🔍 Memproses {target_name}...")

        candidates = []
        
        # 1. Scraping profil pengguna
        if is_user:
            u_clean = kw_clean[1:].strip()
            try:
                user_ref = refs.resolve_user(u_clean)
                res_u = users.get_threads(user_ref)
                candidates.extend(res_u.get('threads', []))
                print(f"   ⚡ Mendapatkan {len(candidates)} threads dari profil @{u_clean}")
            except Exception as e:
                print(f"   ⚠️ Gagal mengambil profil @{u_clean}: {e}")
        else:
            # 2. Scraping pencarian post: Recent & Top
            try:
                r_rec = discovery.search_posts(kw_clean, sort="recent")
                th_rec = r_rec.get('threads', [])
                candidates.extend(th_rec)
                print(f"   ⚡ Tab Recent : {len(th_rec)} threads ditemukan")
            except Exception as e:
                print(f"   ⚠️ Tab Recent error: {e}")

            try:
                r_top = discovery.search_posts(kw_clean, sort="top")
                th_top = r_top.get('threads', [])
                candidates.extend(th_top)
                print(f"   ⚡ Tab Top    : {len(th_top)} threads ditemukan")
            except Exception as e:
                print(f"   ⚠️ Tab Top error: {e}")

            # 3. Scraping Hashtag jika 1-2 kata
            clean_tag = kw_clean.replace(" ", "").lower()
            if len(clean_tag) >= 3 and len(kw_clean.split()) <= 2:
                try:
                    r_tag = discovery.search_tag({"name": clean_tag})
                    th_tag = r_tag.get('threads', [])
                    candidates.extend(th_tag)
                    if th_tag:
                        print(f"   ⚡ Tag #{clean_tag} : {len(th_tag)} threads ditemukan")
                except Exception:
                    pass

        # Evaluasi kandidat threads
        kw_added = 0
        skipped_dup = 0
        skipped_date = 0

        for thread in candidates:
            posts = thread.get('posts', [])
            if not posts:
                continue
            p = posts[0]

            post_link = p.get('link') or f"https://www.threads.net/p/{p.get('code')}"
            if not post_link:
                continue

            # Deduplikasi
            if post_link in seen_urls:
                skipped_dup += 1
                continue

            pub_at = p.get('published_at')
            if not pub_at:
                continue

            try:
                dt_utc = datetime.fromisoformat(pub_at.replace('Z', '+00:00'))
                dt_wib = dt_utc.astimezone(WIB)
                date_str = dt_wib.strftime('%Y-%m-%d')
                time_wib_str = dt_wib.strftime('%Y-%m-%d %H:%M:%S') + ' WIB'
            except Exception:
                continue

            # Verifikasi Rentang Tanggal
            if not (since_str <= date_str <= until_str):
                skipped_date += 1
                continue

            content = (p.get('text', '') or '').strip()
            if not content:
                continue

            # Format konten
            clean_content = content.replace('\r', '').replace('\n', ' | ')

            author_data = p.get('author') or {}
            handle = f"@{author_data.get('username')}" if author_data.get('username') else "@threads_user"

            # Deteksi topik penelitian
            topic = None
            if detect_topic:
                topic = detect_topic(clean_content)
            if not topic:
                topic = "Menteri_PU" if any(w in kw_clean.lower() for w in ['menteri', 'dody', 'diana']) else "Kementerian_PU"

            stats = p.get('stats', {}) or {}
            likes = stats.get('like_count', 0)
            replies = stats.get('reply_count', 0)
            reposts = stats.get('repost_count', 0)
            shares = stats.get('share_count', 0)

            record = {
                'platform': 'Threads',
                'keyword': kw_clean,
                'url': post_link,
                'handle': handle,
                'content': clean_content,
                'created_at': time_wib_str,
                'likes': likes,
                'comments': replies,
                'reposts': reposts,
                'shares': shares,
                'views': 0,
                'scraped_at': datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S') + ' WIB',
                'topic': topic
            }

            seen_urls.add(post_link)
            all_records.append(record)
            kw_added += 1
            total_added_session += 1

            # Log langsung tiap postingan yang lolos
            snip = clean_content[:65]
            print(f"   ✨ [{dt_wib.strftime('%d-%m %H:%M')}] {handle:<20} | ❤️ {likes:<4} | {snip}...")

        # Simpan checkpoint otomatis per keyword
        if kw_added > 0:
            total_now = save_to_csv(all_records, CSV_PATH)
            print(f"   💾 [AUTO-SAVE] +{kw_added} data baru disimpan (Total CSV: {total_now:,} baris)")
        else:
            print(f"   ℹ️ 0 data baru lolos (Duplikat: {skipped_dup}, Di luar tanggal target: {skipped_date})")

        time.sleep(0.6)

    # Laporan Akhir
    print("\n" + "=" * 70)
    print("🎉 SELESAI!")
    print(f"   - Tambahan data baru sesi ini  : +{total_added_session:,} baris")
    print(f"   - Total database akhir         : {len(all_records):,} baris")
    print(f"   - Disimpan di                  : {CSV_PATH}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Threads Scraper Interaktif & Cepat (GraphQL API)")
    parser.add_argument('keywords', nargs='*', help="Kata kunci pencarian atau @username")
    parser.add_argument('--since', default=DEFAULT_SINCE, help=f"Tanggal awal YYYY-MM-DD (default: {DEFAULT_SINCE})")
    parser.add_argument('--until', default=DEFAULT_UNTIL, help=f"Tanggal akhir YYYY-MM-DD (default: {DEFAULT_UNTIL})")
    parser.add_argument('--all', action='store_true', help="Jalankan 12 keyword resmi proyek Kemen PU dari cell_02_config")
    parser.add_argument('--expanded', action='store_true', help="Jalankan 12 keyword resmi + singkatan netizen & akun kedinasan Threads")
    
    args = parser.parse_args()

    # 1. Mode --expanded: 12 keyword resmi + variasi akun & singkatan
    if args.expanded:
        kw_list = OFFICIAL_12_KEYWORDS + EXPANDED_EXTRAS
    # 2. Mode --all: 12 keyword resmi murni cell_02_config.py
    elif args.all:
        kw_list = OFFICIAL_12_KEYWORDS
    # 3. Mode argumen CLI: python scrape_threads.py "kw 1" "kw 2"
    elif args.keywords:
        kw_list = args.keywords
    # 4. Mode interaktif: tanya ke user jika tanpa argumen
    else:
        print("=" * 65)
        print("🧵 THREADS SCRAPER: MODE INTERAKTIF")
        print("=" * 65)
        print("Pilihan cepat: Tekan ENTER langsung untuk 12 keyword resmi Kemen PU.")
        print("-" * 65)
        
        user_kw = input("👉 Masukkan kata kunci (pisahkan dengan koma) atau tekan ENTER: ").strip()
        if user_kw:
            kw_list = [k.strip() for k in user_kw.split(',') if k.strip()]
        else:
            print("   [INFO] Menggunakan 12 keyword resmi proyek Kemen PU.")
            kw_list = OFFICIAL_12_KEYWORDS

        user_since = input(f"👉 Tanggal mulai YYYY-MM-DD (default: {DEFAULT_SINCE}): ").strip()
        since_val = user_since if user_since else DEFAULT_SINCE

        user_until = input(f"👉 Tanggal akhir YYYY-MM-DD (default: {DEFAULT_UNTIL}): ").strip()
        until_val = user_until if user_until else DEFAULT_UNTIL

        run_scraper(kw_list, since_val, until_val)
        return

    run_scraper(kw_list, args.since, args.until)

if __name__ == '__main__':
    main()
