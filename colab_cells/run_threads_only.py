import os
import sys
import time
import pandas as pd
try:
    from cell_02_config import PRIMARY_TOPICS, TOPICS, OUTPUT_DIR, detect_topic
except ImportError:
    from cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
    PRIMARY_TOPICS = {
        "Kementerian_PU": ["Kementerian Pekerjaan Umum"],
        "Menteri_PU": ["Menteri Pekerjaan Umum"],
    }
from cell_08_threads import scrape_threads, load_seen_urls, reset_tracking

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Default proses SEMUA 5 keywords per topik dari cell_02_config (total 10 keywords)
is_primary_only = '--primary-only' in sys.argv
active_topics = PRIMARY_TOPICS if is_primary_only else TOPICS
total_keywords = sum(len(kws) for kws in active_topics.values())

print("=" * 60)
print(f"🚀 MEMULAI SCRAPING THREADS ({len(active_topics)} Topik, {total_keywords} Variasi Keyword)")
print("📊 Target Kuota:")
print("   - Keyword Pertama per Topik : 10.000 data")
print("   - Seluruh Keyword Sisanya   : 1.000 data")
print(f"   - Total Keyword Diproses    : {total_keywords} Keyword (5 Kementerian_PU + 5 Menteri_PU)")
print("🎯 Folder Output: " + str(OUTPUT_DIR))
print("🔍 Tab: Recent (kronologis, hasil lebih relevan)")
print("🔄 Auto-Resume & Smart Refill: Aktif")
print("=" * 60)

all_results = []
current_kw = 1

temp_path = os.path.join(OUTPUT_DIR, "scraped_Threads_Only.csv")

# AUTO-RESUME: Cek CSV yang sudah ada
if os.path.exists(temp_path):
    try:
        try:
            df_existing = pd.read_csv(temp_path, encoding='utf-8-sig')
        except Exception:
            df_existing = pd.read_csv(temp_path)

        all_results = df_existing.to_dict('records')

        # Load existing URLs untuk deduplikasi global
        if 'url' in df_existing.columns:
            existing_urls = set(df_existing['url'].dropna().unique())
            load_seen_urls(existing_urls)

        print(f"[INFO] Melanjutkan dari file yang ada!")
        print(f"       - {len(all_results):,} data sudah tersimpan di CSV")
    except Exception as e:
        print(f"[WARN] Gagal membaca CSV lama: {e}")
        reset_tracking()
else:
    reset_tracking()

for topic, keywords in active_topics.items():
    print(f"\n{'=' * 40}")
    print(f"[{topic}] Memproses {len(keywords)} keyword...")
    print(f"{'=' * 40}")

    for i, kw in enumerate(keywords):
        target_results = 10000 if (is_primary_only or i == 0) else 1000

        # SMART QUOTA REFILL
        current_count = 0
        if len(all_results) > 0:
            current_count = sum(1 for r in all_results if r.get('keyword') == kw)

        is_targeted = bool(os.environ.get('SCRAPE_TARGETED'))
        if not is_targeted and current_count >= target_results:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [SKIP: sudah memenuhi target {current_count}/{target_results} data]")
            current_kw += 1
            continue

        needed = target_results if is_targeted else (target_results - current_count)
        if current_count > 0 and not is_targeted:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [REFILL: {current_count}/{target_results} data, mencari {needed} data lagi...]")
        else:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {needed} data{' [TARGETED MODE]' if is_targeted else ''})")

        try:
            data = scrape_threads(kw, max_results=needed)

            valid_data = []
            for d in data:
                t_match = detect_topic(d.get('content', '')) or d.get('topic') or topic
                if t_match:
                    d['topic'] = t_match
                    valid_data.append(d)
                else:
                    d['topic'] = topic
                    valid_data.append(d)

            all_results.extend(valid_data)

            # SIMPAN LANGSUNG + DEDUPLIKASI by URL (Primary Key)
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

            df_temp.to_csv(temp_path, index=False, encoding='utf-8-sig')
            print(f"  [OK] Tersimpan! Total data Threads unik di CSV: {len(df_temp):,} baris")

        except KeyboardInterrupt:
            print("\n\n  [!] DIHENTIKAN OLEH USER (Ctrl+C) — menyimpan data yang sudah terkumpul...")
            df_save = pd.DataFrame(all_results)
            if 'url' in df_save.columns and len(df_save) > 0:
                mask_has_url = df_save['url'].notna() & (df_save['url'] != '')
                df_with_url = df_save[mask_has_url].drop_duplicates(subset=['url'], keep='first')
                df_no_url = df_save[~mask_has_url]
                df_save = pd.concat([df_with_url, df_no_url], ignore_index=True)
            df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
            print(f"  [OK] {len(df_save)} data tersimpan ke {temp_path}")
            sys.exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal pada keyword '{kw}': {e}")
            if all_results:
                df_save = pd.DataFrame(all_results)
                df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
                print(f"  [SAVE] Data tersimpan ({len(df_save)} baris) sebelum restart.")

            print("  [INFO] Merestart Chrome untuk keyword berikutnya...")
            import cell_08_threads
            if cell_08_threads.THREADS_DRIVER is not None:
                try:
                    cell_08_threads.THREADS_DRIVER.quit()
                except Exception:
                    pass
            cell_08_threads.THREADS_DRIVER = None
            cell_08_threads._kill_zombie_chrome()
            time.sleep(3)

        current_kw += 1

# Final dedup & save (URL sebagai Primary Key)
df_final = pd.DataFrame(all_results)
if 'url' in df_final.columns and len(df_final) > 0:
    mask_has_url = df_final['url'].notna() & (df_final['url'] != '')
    df_with_url = df_final[mask_has_url].drop_duplicates(subset=['url'], keep='first')
    df_no_url = df_final[~mask_has_url]
    df_final = pd.concat([df_with_url, df_no_url], ignore_index=True)
df_final.to_csv(temp_path, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"🎉 SELESAI! Total {len(df_final):,} data Threads unik berhasil disimpan ke:")
print(temp_path)
if 'topic' in df_final.columns and len(df_final) > 0:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
print("=" * 60)
