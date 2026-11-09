import os
import sys
import time
import pandas as pd

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
from cell_06_news import scrape_news, NEWS_EXTRA_KEYWORDS

print("=" * 60)
print("MEMULAI SCRAPING NEWS (Google News + Bing News)")
print("📊 Target Kuota Per-Keyword:")
print("   - Keyword Pertama per Topik : 10.000 data")
print("   - Seluruh Keyword Sisanya   : 1.000 data")
print("🎯 Output Dir: " + str(OUTPUT_DIR))
print("=" * 60)

# Gabungkan TOPICS + NEWS_EXTRA_KEYWORDS jika ada
all_keywords = {}
for topic, keywords in TOPICS.items():
    combined = list(keywords)  # copy
    if topic in NEWS_EXTRA_KEYWORDS:
        for kw in NEWS_EXTRA_KEYWORDS[topic]:
            if kw not in combined:
                combined.append(kw)
    all_keywords[topic] = combined

total_keywords = sum(len(kws) for kws in all_keywords.values())
print(f"[INFO] Total keywords: {total_keywords}")

all_results = []
current_kw = 1
temp_path = os.path.join(OUTPUT_DIR, "scraped_News_Only.csv")

# AUTO-RESUME: Cek CSV yang sudah ada
if os.path.exists(temp_path):
    try:
        df_existing = pd.read_csv(temp_path, encoding='utf-8-sig')
    except Exception:
        try:
            df_existing = pd.read_csv(temp_path)
        except Exception:
            df_existing = None

    if df_existing is not None and len(df_existing) > 0:
        all_results = df_existing.to_dict('records')
        print(f"[INFO] Melanjutkan dari file yang ada! ({len(all_results):,} artikel sudah tersimpan)")

for topic, keywords in all_keywords.items():
    print(f"\n{'='*50}")
    print(f"[{topic}] Memproses {len(keywords)} keyword...")
    print(f"{'='*50}")
    
    for i, kw in enumerate(keywords):
        # Target kuota: Keyword pertama ambil 10.000 data, sisanya 1.000 data
        target_results = 10000 if i == 0 else 1000
        
        # SMART QUOTA REFILL
        current_count = 0
        if len(all_results) > 0:
            current_count = sum(1 for r in all_results if r.get('keyword') == kw)

        is_targeted = bool(os.environ.get('SCRAPE_TARGETED'))
        if not is_targeted and current_count >= target_results:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [SKIP: sudah {current_count}/{target_results} data]")
            current_kw += 1
            continue

        needed = target_results if is_targeted else (target_results - current_count)
        if current_count > 0 and not is_targeted:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [REFILL: {current_count}/{target_results} data, mencari {needed} data lagi...]")
        else:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {needed} data{' [TARGETED MODE]' if is_targeted else ''})")
        
        try:
            data = scrape_news(kw, max_results=needed)
            valid_data = []
            for d in data:
                # In-flight topic validation dengan gabungan judul & deskripsi
                full_text = f"{d.get('content', '')} {d.get('description', '')}"
                t_match = detect_topic(full_text) or d.get('topic') or topic
                d['topic'] = t_match
                valid_data.append(d)

            all_results.extend(valid_data)
            print(f"  [OK] +{len(valid_data)} artikel baru untuk '{kw}' (Google + Bing)")

            # Deduplikasi & Simpan Incremental setiap keyword selesai (URL sebagai Primary Key)
            df_temp = pd.DataFrame(all_results)
            if len(df_temp) > 0:
                if 'url' in df_temp.columns:
                    df_temp.drop_duplicates(subset=['url'], keep='first', inplace=True)
                
                # Standarisasi kolom
                cols_order = ['post_id', 'platform', 'source', 'author', 'handle', 'content', 'description', 'created_at', 'url', 'keyword', 'scraped_at', 'topic']
                ordered = [c for c in cols_order if c in df_temp.columns] + [c for c in df_temp.columns if c not in cols_order]
                df_temp = df_temp[ordered]
                
                df_temp.to_csv(temp_path, index=False, encoding='utf-8-sig')
                all_results = df_temp.to_dict('records')
                print(f"  [SAVE] Total data unik di CSV: {len(df_temp):,} baris")

        except KeyboardInterrupt:
            print("\n\n  [!] DIHENTIKAN OLEH USER (Ctrl+C) — menyimpan data yang sudah terkumpul...")
            df_save = pd.DataFrame(all_results)
            if len(df_save) > 0:
                if 'url' in df_save.columns: df_save.drop_duplicates(subset=['url'], keep='first', inplace=True)
                df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
                print(f"  [OK] {len(df_save)} data tersimpan ke {temp_path}")
            sys.exit(0)
        except Exception as e:
            print(f"  [ERROR] Gagal scrape '{kw}': {e}")
        
        current_kw += 1

# Final save (URL sebagai Primary Key)
df_final = pd.DataFrame(all_results)
if len(df_final) > 0:
    if 'url' in df_final.columns: df_final.drop_duplicates(subset=['url'], keep='first', inplace=True)
    df_final.to_csv(temp_path, index=False, encoding='utf-8-sig')

print(f"\n{'='*60}")
print(f"SELESAI! Total {len(df_final)} artikel unik disimpan ke:")
print(temp_path)
if len(df_final) > 0 and 'topic' in df_final.columns:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
if len(df_final) > 0 and 'source' in df_final.columns:
    print(f"\nDistribusi sumber:")
    print(df_final['source'].value_counts().to_string())
print("=" * 60)
