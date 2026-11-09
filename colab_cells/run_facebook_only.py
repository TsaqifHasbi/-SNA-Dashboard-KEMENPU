import os
import sys

# Fix Windows console encoding SEBELUM import apapun (cell_02_config mencetak emoji)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import pandas as pd
from cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
from cell_09_facebook import (
    scrape_facebook,
    load_seen_urls,
    reset_tracking,
    _force_relogin,
    FB_PROFILE_DIR,
    enrich_single_facebook_post
)

temp_path = os.path.join(OUTPUT_DIR, "scraped_Facebook_Only.csv")

# OPSI FRESH LOGIN / RELOGIN VIA ARGUMENT
if '--relogin' in sys.argv or '--fresh-login' in sys.argv:
    print("[INFO] Parameter --relogin terdeteksi: mereset session untuk login akun baru...")
    _force_relogin()

# OPSI PERBAIKI CAPTION TERPOTONG PADA CSV LAMA
if '--fix-truncated' in sys.argv or '--rescue-truncated' in sys.argv:
    print("\n" + "=" * 60)
    print("🛠️ MODE RESCUE: MEMPERBAIKI CAPTION FACEBOOK TERPOTONG PADA CSV")
    print("=" * 60)
    if not os.path.exists(temp_path):
        print(f"[ERROR] File {temp_path} tidak ditemukan!")
        sys.exit(1)

    try:
        df_fb = pd.read_csv(temp_path, encoding='utf-8-sig')
    except:
        df_fb = pd.read_csv(temp_path)

    print(f"[INFO] Total data di CSV: {len(df_fb):,} baris")
    is_trunc = (
        df_fb['content'].isna() |
        df_fb['content'].str.contains(r'(\.\.\.|…)\s*$', regex=True, na=False) |
        df_fb['content'].str.contains(r'\b(see more|lihat selengkapnya|selengkapnya)\b', case=False, na=False) |
        (df_fb['content'].str.len() < 70)
    )
    idx_to_fix = df_fb[is_trunc].index.tolist()
    print(f"[TARGET] Ditemukan {len(idx_to_fix):,} postingan Facebook dengan caption terindikasi terpotong.")

    if not idx_to_fix:
        print("[OK] Semua caption Facebook di CSV sudah lengkap!")
        sys.exit(0)

    backup_file = os.path.join(OUTPUT_DIR, f"scraped_Facebook_Only_BEFORE_RESCUE.csv")
    df_fb.to_csv(backup_file, index=False, encoding='utf-8-sig')
    print(f"[BACKUP] File cadangan disimpan ke: {backup_file}\n")

    fixed_count = 0
    try:
        for step, idx in enumerate(idx_to_fix, 1):
            row = df_fb.loc[idx]
            url_post = row.get('url', '')
            old_content = str(row.get('content', ''))
            print(f"[{step}/{len(idx_to_fix)}] Membuka URL: {url_post}")
            print(f"  Old ({len(old_content)} char): {repr(old_content[:70])}...")

            details = enrich_single_facebook_post(url_post)
            new_content = details.get('caption', '')
            if new_content and len(new_content) > len(old_content):
                df_fb.loc[idx, 'content'] = new_content
                if details.get('likes') and str(details['likes']).isdigit() and int(details['likes']) > row.get('likes', 0):
                    df_fb.loc[idx, 'likes'] = int(details['likes'])
                fixed_count += 1
                print(f"  [RESCUED] Berhasil diperluas: {len(old_content)} -> {len(new_content)} karakter!")
            else:
                print(f"  [KEEP] Panjang sama atau tidak ada perubahan.")

            if step % 10 == 0:
                df_fb.to_csv(temp_path, index=False, encoding='utf-8-sig')
                print(f"  [CHECKPOINT] Disimpan ke CSV ({fixed_count} diperbaiki sejauh ini).")

            time.sleep(1.8)

    except KeyboardInterrupt:
        print("\n[!] Dihentikan user (Ctrl+C). Menyimpan hasil...")
    finally:
        df_fb.to_csv(temp_path, index=False, encoding='utf-8-sig')
        print(f"\n[SELESAI] Total {fixed_count} caption Facebook berhasil diperluas ke {temp_path}!")
        sys.exit(0)

print("=" * 60)
print("🚀 MEMULAI SCRAPING FACEBOOK ONLY (STRICT FULL CAPTIONS)")
print("📊 Target Kuota Per-Keyword:")
print("   - Keyword Pertama per Topik : 10.000 data")
print("   - Seluruh Keyword Sisanya   : 1.000 data")
print("🎯 Mode: Full Multi-Keyword Crawl (Memproses seluruh variasi keyword hingga kuota terpenuhi)")
print("🔄 Auto-Resume: Aktif (skip keyword yang sudah selesai)")
print("💾 Auto-Save  : Langsung tersimpan ke CSV setiap 1 keyword selesai")
print("=" * 60)

all_results = []
total_keywords = sum(len(kws) for kws in TOPICS.values())
current_kw = 1

temp_path = os.path.join(OUTPUT_DIR, "scraped_Facebook_Only.csv")
existing_keywords = set()

# OPSI FRESH START / RE-SCRAPE VIA ARGUMENT
is_fresh = '--fresh' in sys.argv or '--reset' in sys.argv

# AUTO-RESUME vs FRESH START: Cek CSV yang sudah ada
if os.path.exists(temp_path) and not is_fresh:
    try:
        try:
            df_existing = pd.read_csv(temp_path, encoding='utf-8-sig')
        except Exception:
            df_existing = pd.read_csv(temp_path)

        if 'keyword' in df_existing.columns:
            existing_keywords = set(df_existing['keyword'].dropna().unique())
        all_results = df_existing.to_dict('records')

        # Load existing URLs untuk deduplikasi global
        if 'url' in df_existing.columns:
            existing_urls = set(df_existing['url'].dropna().unique())
            load_seen_urls(existing_urls)

        print(f"[INFO] Melanjutkan dari file yang ada!")
        print(f"       - {len(existing_keywords)} keyword sudah selesai di-scrape")
        print(f"       - {len(all_results)} data sudah tersimpan di CSV")
        print(f"       (Gunakan flag --fresh jika ingin mengulang scraping dari awal)")
    except Exception as e:
        print(f"[WARN] Gagal membaca CSV lama: {e}")
        reset_tracking()
else:
    if is_fresh and os.path.exists(temp_path):
        import shutil
        backup_p = os.path.join(OUTPUT_DIR, "scraped_Facebook_Only_BACKUP.csv")
        try:
            shutil.copy2(temp_path, backup_p)
            print(f"[BACKUP] File CSV lama diamankan ke {backup_p}")
        except Exception as e:
            print(f"[WARN] Gagal backup: {e}")
        print("[RESET] Memulai scraping Facebook dari awal (Fresh Start)...")
    reset_tracking()

print()
print("=" * 60)
print("[OK] KONFIGURASI SELESAI")
print(f"[INFO] Topik: {len(TOPICS)} topik")
print(f"[INFO] Keywords: {total_keywords} total variasi keyword")
print("=" * 60)

for topic, keywords in TOPICS.items():
    print(f"\n{'=' * 40}")
    print(f"[{topic}] Memproses {len(keywords)} keyword...")
    print(f"{'=' * 40}")

    for i, kw in enumerate(keywords):
        # 1 keyword utama per topik ambil 10.000 data, sisanya 1.000 data
        target_results = 10000 if i == 0 else 1000

        print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {target_results} data)")

        # SMART QUOTA REFILL: Cek berapa data yang sudah ada di CSV untuk keyword ini
        current_count = 0
        if len(all_results) > 0:
            current_count = sum(1 for r in all_results if r.get('keyword') == kw)

        is_targeted = bool(os.environ.get('SCRAPE_TARGETED'))
        if not is_targeted and current_count >= target_results:
            print(f"  [SKIP] Keyword '{kw}' sudah memenuhi target ({current_count}/{target_results} data).")
            current_kw += 1
            continue

        needed = target_results if is_targeted else (target_results - current_count)
        if current_count > 0 and not is_targeted:
            print(f"  [REFILL] Keyword '{kw}' baru ada {current_count}/{target_results} data. Melanjutkan ambil {needed} data lagi...")
        else:
            print(f"  [START] Mengambil target {needed} data untuk '{kw}'{' [TARGETED MODE]' if is_targeted else ''}...")

        try:
            data = scrape_facebook(kw, max_results=needed)

            # Validasi regulasi topik tingkat kedua untuk menjamin 100% data lolos sorting
            valid_data = []
            for d in data:
                t_match = detect_topic(d.get('content', '')) or d.get('topic') or topic
                if t_match:
                    d['topic'] = t_match
                    valid_data.append(d)

            all_results.extend(valid_data)

            # SIMPAN LANGSUNG + DEDUPLIKASI by URL
            df_temp = pd.DataFrame(all_results)
            if 'url' in df_temp.columns and len(df_temp) > 0:
                before = len(df_temp)
                mask_has_url = df_temp['url'].notna() & (df_temp['url'] != '')
                df_with_url = df_temp[mask_has_url].drop_duplicates(subset=['url'], keep='first')
                df_no_url = df_temp[~mask_has_url]
                df_temp = pd.concat([df_with_url, df_no_url], ignore_index=True)
                removed = before - len(df_temp)
                if removed > 0:
                    print(f"  [DEDUP] Dihapus {removed} duplikat URL.")
                    all_results = df_temp.to_dict('records')

            # Standarisasi urutan kolom
            cols_order = ['post_id', 'platform', 'post_type', 'author', 'handle', 'content', 'created_at', 'likes', 'comments', 'shares', 'url', 'keyword', 'scraped_at', 'topic', 'description']
            ordered = [c for c in cols_order if c in df_temp.columns] + [c for c in df_temp.columns if c not in cols_order]
            df_temp = df_temp[ordered]

            df_temp.to_csv(temp_path, index=False, encoding='utf-8-sig')
            print(f"  [OK] Tersimpan! Total data Facebook di CSV: {len(df_temp):,} baris")

        except KeyboardInterrupt:
            print("\n\n  [!] DIHENTIKAN OLEH USER (Ctrl+C) — menyimpan data yang sudah terkumpul...")
            df_save = pd.DataFrame(all_results)
            if 'url' in df_save.columns and len(df_save) > 0:
                mask_has_url = df_save['url'].notna() & (df_save['url'] != '')
                df_with_url = df_save[mask_has_url].drop_duplicates(subset=['url'], keep='first')
                df_no_url = df_save[~mask_has_url]
                df_save = pd.concat([df_with_url, df_no_url], ignore_index=True)
            cols_order = ['post_id', 'platform', 'post_type', 'author', 'handle', 'content', 'created_at', 'likes', 'comments', 'shares', 'url', 'keyword', 'scraped_at', 'topic', 'description']
            ordered = [c for c in cols_order if c in df_save.columns] + [c for c in df_save.columns if c not in cols_order]
            df_save = df_save[ordered]
            df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
            print(f"  [OK] {len(df_save)} data tersimpan ke {temp_path}")
            print("  [INFO] Jalankan ulang script ini kapan saja untuk melanjutkan (auto-resume).")
            sys.exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal/terputus pada keyword '{kw}': {e}")
            if all_results:
                df_save = pd.DataFrame(all_results)
                df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
                print(f"  [SAVE] Data tersimpan ({len(df_save)} baris) sebelum recovery.")

            print("  [INFO] Merestart Chrome untuk keyword berikutnya...")
            import cell_09_facebook
            try:
                if cell_09_facebook.FB_DRIVER is not None:
                    cell_09_facebook.FB_DRIVER.quit()
            except Exception:
                pass
            cell_09_facebook.FB_DRIVER = None
            time.sleep(3)

        current_kw += 1

# Final dedup & save
df_final = pd.DataFrame(all_results)
if 'url' in df_final.columns and len(df_final) > 0:
    mask_has_url = df_final['url'].notna() & (df_final['url'] != '')
    df_with_url = df_final[mask_has_url].drop_duplicates(subset=['url'], keep='first')
    df_no_url = df_final[~mask_has_url]
    df_final = pd.concat([df_with_url, df_no_url], ignore_index=True)

cols_order = ['post_id', 'platform', 'post_type', 'author', 'handle', 'content', 'created_at', 'likes', 'comments', 'shares', 'url', 'keyword', 'scraped_at', 'topic', 'description']
ordered = [c for c in cols_order if c in df_final.columns] + [c for c in df_final.columns if c not in cols_order]
df_final = df_final[ordered]
df_final.to_csv(temp_path, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"🎉 SELESAI! Total {len(df_final)} data Facebook unik berhasil disimpan ke:")
print(temp_path)
if 'topic' in df_final.columns and len(df_final) > 0:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
print("=" * 60)
