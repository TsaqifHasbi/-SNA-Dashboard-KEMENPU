import os
import sys
import re
import time
import pandas as pd

# Fix Windows console encoding SEBELUM import apapun (cell_02_config mencetak emoji)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

try:
    from cell_02_config import PRIMARY_TOPICS, TOPICS, OUTPUT_DIR, detect_topic
except ImportError:
    from cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
    PRIMARY_TOPICS = {
        "Kementerian_PU": ["Kementerian Pekerjaan Umum"],
        "Menteri_PU": ["Menteri Pekerjaan Umum"],
    }
from cell_07_instagram import (
    scrape_instagram,
    load_seen_urls,
    reset_tracking,
    enrich_single_instagram_post,
    IG_DRIVER
)

# Sesuai standar cell_02_config.py:
# - Keyword Pertama per Topik : 10.000 data
# - Seluruh Keyword Sisanya   : 1.000 data
active_topics = TOPICS
total_keywords = sum(len(kws) for kws in active_topics.values())

print("=" * 60)
print("🚀 MEMULAI SCRAPING INSTAGRAM (PROJECT KEMEN PU RI)")
print("📊 Target Kuota Sesuai Config:")
print("   - Keyword Pertama per Topik : 10.000 data")
print("   - Seluruh Keyword Sisanya   : 1.000 data")
print(f"   - Total Keyword             : {total_keywords} Keyword (5 Kementerian_PU + 5 Menteri_PU)")
print("🎯 Folder Output: " + str(OUTPUT_DIR))
print("🔍 Fitur Unggulan:")
print("   - Auto-Expand '... more' / '... selengkapnya' pada setiap post")
print("   - Multi-Source Caption (JSON-LD Schema.org + GraphQL + DOM)")
print("   - Smart Quota Refill (hanya mengambil kekurangan data per keyword)")
print("=" * 60)

temp_path = os.path.join(OUTPUT_DIR, "scraped_Instagram_Only.csv")

# ==============================================================================
# MODE RESCUE / FIX TRUNCATED CAPTIONS (Opsional via flag --fix-truncated)
# ==============================================================================
if '--fix-truncated' in sys.argv or '--rescue-truncated' in sys.argv:
    print("\n" + "=" * 60)
    print("🛠️ MODE RESCUE: MEMPERBAIKI CAPTION TERPOTONG PADA CSV LAMA")
    print("=" * 60)
    if not os.path.exists(temp_path):
        print(f"[ERROR] File {temp_path} tidak ditemukan!")
        sys.exit(1)

    df_ig = pd.read_csv(temp_path)
    print(f"[INFO] Total data di CSV: {len(df_ig):,} baris")

    # Identifikasi baris yang terindikasi terpotong
    is_trunc = (
        df_ig['content'].isna() |
        df_ig['content'].str.contains(r'(\.\.\.|…)\s*$', regex=True, na=False) |
        df_ig['content'].str.contains(r'\b(more|selengkapnya)\b', case=False, na=False) |
        (df_ig['content'].str.len() < 60)
    )
    idx_to_fix = df_ig[is_trunc].index.tolist()
    print(f"[TARGET] Ditemukan {len(idx_to_fix):,} postingan dengan caption terindikasi terpotong.")

    if not idx_to_fix:
        print("[OK] Semua caption di CSV sudah lengkap! Tidak ada yang perlu diperbaiki.")
        sys.exit(0)

    # Backup sebelum perbaikan
    backup_file = os.path.join(OUTPUT_DIR, f"scraped_Instagram_Only_BEFORE_RESCUE.csv")
    df_ig.to_csv(backup_file, index=False)
    print(f"[BACKUP] File cadangan disimpan ke: {backup_file}\n")

    fixed_count = 0
    try:
        for step, idx in enumerate(idx_to_fix, 1):
            row = df_ig.loc[idx]
            url_post = row.get('url', '')
            old_content = str(row.get('content', ''))
            print(f"[{step}/{len(idx_to_fix)}] Membuka URL: {url_post}")
            print(f"  Old ({len(old_content)} char): {repr(old_content[:70])}...")

            details = enrich_single_instagram_post(url_post)
            new_content = details.get('content', '')
            if new_content and len(new_content) > len(old_content):
                df_ig.loc[idx, 'content'] = new_content.replace('\n', ' | ').replace('\r', '')
                if details.get('likes') and details['likes'] > row.get('likes', 0):
                    df_ig.loc[idx, 'likes'] = details['likes']
                fixed_count += 1
                print(f"  [RESCUED] Berhasil diperluas: {len(old_content)} -> {len(new_content)} karakter!")
            else:
                print(f"  [KEEP] Panjang sama atau tidak ada perubahan.")

            # Simpan berkala tiap 10 data
            if step % 10 == 0:
                df_ig.to_csv(temp_path, index=False)
                print(f"  [CHECKPOINT] Disimpan ke CSV ({fixed_count} diperbaiki sejauh ini).")

            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\n[!] Dihentikan user (Ctrl+C). Menyimpan hasil yang sudah diperbaiki...")
    finally:
        df_ig.to_csv(temp_path, index=False)
        print(f"\n[SELESAI] Total {fixed_count} caption berhasil diperluas dan disimpan ke {temp_path}!")
        sys.exit(0)

# ==============================================================================
# MODE REGULER: SCRAPING DENGAN SMART QUOTA REFILL
# ==============================================================================
all_results = []
existing_keywords = set()

is_fresh = '--fresh' in sys.argv or '--reset' in sys.argv

# AUTO-RESUME vs FRESH START: Cek CSV yang sudah ada
if os.path.exists(temp_path) and not is_fresh:
    try:
        df_existing = pd.read_csv(temp_path)
        existing_keywords = set(df_existing['keyword'].dropna().unique())
        all_results = df_existing.to_dict('records')

        if 'url' in df_existing.columns:
            existing_urls = set(df_existing['url'].dropna().unique())
            load_seen_urls(existing_urls)

        print(f"[INFO] Melanjutkan dari file yang ada!")
        print(f"       - {len(existing_keywords)} keyword sudah memiliki data")
        print(f"       - {len(all_results)} data sudah tersimpan di CSV")
        print(f"       (Gunakan flag --fresh jika ingin mengulang scraping dari awal)")
    except Exception as e:
        print(f"[WARN] Gagal membaca CSV lama: {e}")
        reset_tracking()
else:
    if is_fresh and os.path.exists(temp_path):
        import shutil
        backup_p = os.path.join(OUTPUT_DIR, "scraped_Instagram_Only_BACKUP.csv")
        try:
            shutil.copy2(temp_path, backup_p)
            print(f"[BACKUP] File CSV lama diamankan ke {backup_p}")
        except Exception as e:
            print(f"[WARN] Gagal backup: {e}")
        try:
            os.remove(temp_path)
        except:
            pass
        print("[RESET] Memulai scraping Instagram dari awal (Fresh Start)...")
    reset_tracking()

CLEAN_CHARS_PATTERN = re.compile(r'[\u2028\u2029\r\x0b\x0c\x85]')

def save_checkpoint(records, filepath):
    """
    Fungsi jaminan penyimpanan langsung ke CSV:
    - Melakukan deduplikasi berbasis 'url'
    - Menata urutan kolom standar
    - Menulis file CSV dengan utf-8-sig
    - Memaksa flush ke disk sistem
    """
    cols_order = [
        'post_id', 'platform', 'post_type', 'author', 'handle',
        'content', 'created_at', 'likes', 'comments', 'url',
        'keyword', 'scraped_at', 'topic', 'description'
    ]
    if len(records) > 0:
        df_save = pd.DataFrame(records)
        if 'url' in df_save.columns:
            before_len = len(df_save)
            mask_has_url = df_save['url'].notna() & (df_save['url'] != '')
            df_with_url = df_save[mask_has_url].drop_duplicates(subset=['url'], keep='first')
            df_no_url = df_save[~mask_has_url]
            df_save = pd.concat([df_with_url, df_no_url], ignore_index=True)
            removed = before_len - len(df_save)
            if removed > 0:
                print(f"  [DEDUP] Dihapus {removed} duplikat URL.")
        ordered = [c for c in cols_order if c in df_save.columns] + [c for c in df_save.columns if c not in cols_order]
        df_save = df_save[ordered]

        # Sanitasi karakter line terminators aneh (\u2028 LS, \u2029 PS, \r) via pure Python regex (100% kompatibel dgn PyArrow/Pandas)
        try:
            for col_name in df_save.columns:
                if col_name in ['content', 'description', 'author', 'handle', 'keyword', 'topic']:
                    df_save[col_name] = df_save[col_name].map(
                        lambda x: CLEAN_CHARS_PATTERN.sub(' ', str(x)) if pd.notna(x) and str(x) != 'nan' else x
                    )
        except Exception:
            pass
    else:
        df_save = pd.DataFrame(columns=cols_order)

    df_save.to_csv(filepath, index=False, encoding='utf-8-sig')
    sys.stdout.flush()
    return len(df_save)

# Dukungan argumen CLI:
# 1. Filter topik spesifik: --topic Kementerian_PU atau --topic Menteri_PU
# 2. Mode 1 keyword utama: --primary-only atau --single-keyword
# 3. Kustom target kuota: --target 2000 atau --limit 5000
selected_topic_arg = None
target_custom_arg = None

for idx, arg in enumerate(sys.argv):
    if arg == '--topic' and idx + 1 < len(sys.argv):
        selected_topic_arg = sys.argv[idx + 1].strip()
    elif arg.startswith('--topic='):
        selected_topic_arg = arg.split('=', 1)[1].strip()
    elif arg in ['--target', '--limit'] and idx + 1 < len(sys.argv):
        try:
            target_custom_arg = int(sys.argv[idx + 1].strip())
        except ValueError:
            pass
    elif arg.startswith('--target=') or arg.startswith('--limit='):
        try:
            target_custom_arg = int(arg.split('=', 1)[1].strip())
        except ValueError:
            pass

# Default memproses seluruh 10 keywords (5 Kementerian_PU + 5 Menteri_PU)
is_primary_only = '--primary-only' in sys.argv
active_topics = PRIMARY_TOPICS if is_primary_only else TOPICS

if selected_topic_arg:
    filtered_topics = {}
    clean_sel = selected_topic_arg.replace(' ', '_').lower()
    for t_key, t_val in active_topics.items():
        if clean_sel == t_key.lower() or clean_sel in t_key.lower() or t_key.lower() in clean_sel:
            filtered_topics[t_key] = t_val
        elif any(clean_sel == str(k).replace(' ', '_').lower() for k in t_val):
            filtered_topics[t_key] = t_val
    if filtered_topics:
        active_topics = filtered_topics
        print(f"\n🎯 [FILTER TOPIK AKTIF] Hanya memproses topik: {list(active_topics.keys())}")
    else:
        print(f"\n[WARN] Topik '{selected_topic_arg}' tidak ditemukan. Menggunakan daftar topik default.")

total_keywords = sum(len(kws) for kws in active_topics.values())
current_kw = 1

for topic, keywords in active_topics.items():
    print(f"\n{'='*40}")
    print(f"[{topic}] Memproses {len(keywords)} keyword...")
    print(f"{'='*40}")

    for i, kw in enumerate(keywords):
        # Target kuota: Mengikuti standar cell_02_config.py
        # Keyword Pertama per Topik = 10.000 data, Keyword berikutnya = 1.000 data
        if target_custom_arg:
            target_results = target_custom_arg
        else:
            target_results = 10000 if (is_primary_only or i == 0) else 1000

        print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {target_results} data)")

        # SMART QUOTA REFILL: Cek berapa data yang sudah ada di CSV untuk keyword ini
        current_count = 0
        if len(all_results) > 0:
            current_count = sum(1 for r in all_results if r.get('keyword') == kw)

        if current_count >= target_results:
            print(f"  [SKIP] Keyword '{kw}' sudah memenuhi target ({current_count}/{target_results} data).")
            current_kw += 1
            continue

        needed = target_results - current_count
        if current_count > 0:
            print(f"  [REFILL] Keyword '{kw}' baru ada {current_count}/{target_results} data. Melanjutkan ambil {needed} data lagi...")
        else:
            print(f"  [START] Keyword '{kw}' belum ada di CSV. Mengambil target {needed} data...")

        # Callback real-time: Tiap ada 1 postingan berhasil diekstrak & lolos regulasi, langsung simpan!
        def on_post_scraped(post_item):
            global all_results
            t_match = detect_topic(post_item.get('content', '')) or post_item.get('topic') or topic
            if t_match:
                post_item['topic'] = t_match
            p_url = post_item.get('url')
            if not p_url or not any(r.get('url') == p_url for r in all_results):
                all_results.append(post_item)
                cur_total = save_checkpoint(all_results, temp_path)
                print(f"        💾 [REAL-TIME FLUSH] +1 post disimpan ke CSV (Total di CSV: {cur_total:,} baris)")

        try:
            data = scrape_instagram(kw, max_results=needed, on_item_scraped=on_post_scraped)

            # Validasi regulasi topik jika ada item dari data yang belum masuk via callback
            valid_data = []
            for d in data:
                t_match = detect_topic(d.get('content', '')) or d.get('topic') or topic
                if t_match:
                    d['topic'] = t_match
                    valid_data.append(d)

            for vd in valid_data:
                v_url = vd.get('url')
                if not v_url or not any(r.get('url') == v_url for r in all_results):
                    all_results.append(vd)

        except KeyboardInterrupt:
            print("\n\n  [!] DIHENTIKAN OLEH USER (Ctrl+C) — menyimpan data yang sudah terkumpul...")
            total_saved = save_checkpoint(all_results, temp_path)
            print(f"  [OK] {total_saved:,} data aman tersimpan ke {temp_path}")
            try:
                import cell_07_instagram
                if cell_07_instagram.IG_DRIVER:
                    cell_07_instagram.IG_DRIVER.quit()
            except Exception:
                pass
            os._exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal/Timeout pada keyword '{kw}': {e}")
            total_saved = save_checkpoint(all_results, temp_path)
            print(f"  [SAVE] Data tersimpan ({total_saved:,} baris) sebelum recovery.")
            print("  [INFO] Merestart Chrome untuk keyword berikutnya...")
            import cell_07_instagram
            try:
                cell_07_instagram._init_driver()
            except Exception:
                cell_07_instagram.IG_DRIVER = None

        finally:
            # JAMINAN 100%: TIAP KEYWORD SELESAI LANGSUNG FLUSH KE CSV
            total_now = save_checkpoint(all_results, temp_path)
            try:
                all_results = pd.read_csv(temp_path, encoding='utf-8-sig').to_dict('records')
            except Exception:
                pass
            print(f"  💾 [SAVED] Keyword [{current_kw}/{total_keywords}] '{kw}' selesai! Total data Instagram tersimpan di CSV: {total_now:,} baris.")
            sys.stdout.flush()

        current_kw += 1

# Final dedup & save
total_final = save_checkpoint(all_results, temp_path)
df_final = pd.read_csv(temp_path, encoding='utf-8-sig')

print("\n" + "="*60)
print(f"🎉 SELESAI! Total {len(df_final):,} data Instagram unik berhasil disimpan ke:")
print(temp_path)
if 'topic' in df_final.columns and len(df_final) > 0:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
print("="*60)
