import os
import sys

# Fix Windows console encoding immediately before any imports print emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import pandas as pd
from cell_02_config import TOPICS, OUTPUT_DIR
from cell_03_youtube import scrape_youtube

print("=" * 60)
print("🚀 MEMULAI SCRAPING YOUTUBE (FULL CRAWL)")
print("📅 Filter: 1 Januari 2025 - Sekarang")
print("🎯 Target: 1000 video untuk 2 keyword utama, 100 untuk sisanya")
print("🔄 Auto-Resume & Smart Refill: Aktif")
print("=" * 60)

all_results = []
total_keywords = sum(len(kws) for kws in TOPICS.values())
current_kw = 1

temp_path = os.path.join(OUTPUT_DIR, "scraped_YouTube_Only.csv")
read_path = temp_path
existing_keywords = set()

# AUTO-RESUME: Cek CSV yang sudah ada
if os.path.exists(read_path):
    try:
        df_existing = pd.read_csv(read_path)
        existing_keywords = set(df_existing['keyword'].dropna().unique())
        all_results = df_existing.to_dict('records')
        print(f"[INFO] Melanjutkan dari file yang ada ({os.path.basename(read_path)})!")
        print(f"       - {len(existing_keywords)} keyword sudah selesai")
        print(f"       - {len(all_results)} data sudah tersimpan")
    except Exception as e:
        print(f"[WARN] Gagal membaca CSV lama: {e}")

print()
print("=" * 60)
print("[OK] KONFIGURASI SELESAI")
print(f"[INFO] Topik: {len(TOPICS)} topik")
print(f"[INFO] Keywords: {total_keywords} variasi keyword")
print("=" * 60)

for topic, keywords in TOPICS.items():
    print(f"\n[TOPIK] {topic}: {len(keywords)} keywords")
    for kw in keywords[:5]:
        print(f"   - {kw}")
    if len(keywords) > 5:
        print(f"   - ... dan {len(keywords) - 5} lainnya")

print()

for topic, keywords in TOPICS.items():
    print(f"\n{'=' * 40}")
    print(f"[{topic}] Memproses {len(keywords)} keyword...")
    print(f"{'=' * 40}")

    for i, kw in enumerate(keywords):
        print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}'")

        # SMART QUOTA REFILL: 2 keyword utama 1000, sisanya 100
        target_results = 10000 if i == 0 else 1000
        current_count = 0
        if len(all_results) > 0:
            current_count = sum(1 for r in all_results if r.get('keyword') == kw)

        if current_count >= target_results:
            print(f"  [SKIP] Keyword '{kw}' sudah memenuhi target ({current_count}/{target_results} data).")
            current_kw += 1
            continue

        needed = target_results - current_count
        if current_count > 0:
            print(f"  [REFILL] Keyword '{kw}' baru ada {current_count}/{target_results} data. Mengambil {needed} data lagi...")
        else:
            print(f"  [START] Keyword '{kw}' belum ada di CSV. Mengambil target {needed} data...")

        try:
            data = scrape_youtube(kw, max_results=needed)

            if data:
                for d in data:
                    d['topic'] = topic
                all_results.extend(data)
                print(f"  [OK] Dapat {len(data)} video dari keyword '{kw}'")
            else:
                print(f"  [INFO] Tidak ada data untuk keyword '{kw}'")

        except SystemExit:
            # Kuota habis — simpan semua data yang sudah terkumpul, lalu keluar
            print("\n[!] KUOTA HABIS — menyimpan data yang sudah terkumpul...")
            df_save = pd.DataFrame(all_results)
            if 'url' in df_save.columns and len(df_save) > 0:
                df_save.drop_duplicates(subset=['url'], inplace=True)
            df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
            print(f"[OK] {len(df_save)} data tersimpan ke {temp_path}")
            print("[INFO] Jalankan ulang script ini setelah kuota reset (~14:00 WIB besok).")
            sys.exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal pada keyword '{kw}': {e}")

        current_kw += 1

        # SIMPAN LANGSUNG + DEDUPLIKASI by URL (Primary Key)
        df_temp = pd.DataFrame(all_results)
        if 'url' in df_temp.columns and len(df_temp) > 0:
            before = len(df_temp)
            df_temp.drop_duplicates(subset=['url'], inplace=True)
            removed = before - len(df_temp)
            if removed > 0:
                print(f"  [DEDUP] Dihapus {removed} duplikat URL.")
                all_results = df_temp.to_dict('records')
        df_temp.to_csv(temp_path, index=False, encoding='utf-8-sig')
        print(f"  [SAVE] Total data di CSV: {len(df_temp)}")

# Final dedup & save (URL sebagai Primary Key)
df_final = pd.DataFrame(all_results)
if 'url' in df_final.columns and len(df_final) > 0:
    df_final.drop_duplicates(subset=['url'], inplace=True)
df_final.to_csv(temp_path, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print("🎉 SELESAI! Scraping YouTube berhasil.")
print(f"📊 Total data final: {len(df_final)} baris")
print(f"📁 Tersimpan di: {temp_path}")
print("=" * 60)
