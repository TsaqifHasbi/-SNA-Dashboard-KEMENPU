import os
import sys
import pandas as pd
try:
    from cell_02_config import PRIMARY_TOPICS, TOPICS, OUTPUT_DIR, detect_topic
except ImportError:
    from cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
    PRIMARY_TOPICS = {
        "Kementerian_PU": ["Kementerian Pekerjaan Umum"],
        "Menteri_PU": ["Menteri Pekerjaan Umum"],
    }
from cell_04_twitter import scrape_twitter, load_seen_urls, reset_tracking

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
print(f"🚀 MEMULAI SCRAPING TWITTER/X ({len(active_topics)} Topik, {total_keywords} Variasi Keyword)")
print("📊 Target Kuota:")
print("   - Keyword Pertama per Topik : 10.000 data")
print("   - Seluruh Keyword Sisanya   : 1.000 data")
print(f"   - Total Keyword Diproses    : {total_keywords} Keyword (5 Kementerian_PU + 5 Menteri_PU)")
print("🎯 Folder Output: " + str(OUTPUT_DIR))
print("🔄 Auto-Resume & Smart Refill: Aktif")
print("=" * 60)

all_results = []
current_kw = 1

temp_path = os.path.join(OUTPUT_DIR, "scraped_Twitter_Only.csv")

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

def save_twitter_checkpoint(records, filepath):
    """
    Fungsi jaminan penyimpanan langsung ke CSV untuk Twitter:
    - Melakukan deduplikasi berbasis 'url'
    - Menata urutan kolom standar
    - Menulis file CSV dengan utf-8-sig
    - Memaksa flush ke disk sistem
    """
    cols_order = [
        'post_id', 'platform', 'post_type', 'author', 'handle',
        'content', 'created_at', 'likes', 'comments', 'retweets', 'url',
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
    else:
        df_save = pd.DataFrame(columns=cols_order)

    df_save.to_csv(filepath, index=False, encoding='utf-8-sig')
    sys.stdout.flush()
    return len(df_save)

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

        if current_count >= target_results:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [SKIP: sudah memenuhi target {current_count}/{target_results} data]")
            current_kw += 1
            continue

        needed = target_results - current_count
        if current_count > 0:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' [REFILL: {current_count}/{target_results} data, mencari {needed} data lagi...]")
        else:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {target_results} data)")

        try:
            data = scrape_twitter(kw, max_results=needed)

            valid_data = []
            for d in data:
                t_match = detect_topic(d.get('content', '')) or d.get('topic') or topic
                if t_match:
                    d['topic'] = t_match
                    valid_data.append(d)
                else:
                    d['topic'] = topic
                    valid_data.append(d)

            for vd in valid_data:
                v_url = vd.get('url')
                if not v_url or not any(r.get('url') == v_url for r in all_results):
                    all_results.append(vd)

        except KeyboardInterrupt:
            print("\n\n  [!] DIHENTIKAN OLEH USER (Ctrl+C) — menyimpan data yang sudah terkumpul...")
            total_saved = save_twitter_checkpoint(all_results, temp_path)
            print(f"  [OK] {total_saved:,} data tersimpan ke {temp_path}")
            sys.exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal pada keyword '{kw}': {e}")
            total_saved = save_twitter_checkpoint(all_results, temp_path)
            print(f"  [SAVE] Data tersimpan ({total_saved:,} baris) sebelum recovery.")
            print("  [INFO] Merestart Chrome untuk keyword berikutnya...")
            import cell_04_twitter
            try:
                cell_04_twitter._init_driver()
            except Exception:
                cell_04_twitter.TWITTER_DRIVER = None

        finally:
            # JAMINAN 100%: TIAP KEYWORD SELESAI LANGSUNG FLUSH KE CSV
            total_now = save_twitter_checkpoint(all_results, temp_path)
            try:
                all_results = pd.read_csv(temp_path, encoding='utf-8-sig').to_dict('records')
            except Exception:
                pass
            print(f"  💾 [SAVED] Keyword [{current_kw}/{total_keywords}] '{kw}' selesai! Total data Twitter tersimpan di CSV: {total_now:,} baris.")
            sys.stdout.flush()

        current_kw += 1

# Final dedup & save (URL sebagai Primary Key)
total_final = save_twitter_checkpoint(all_results, temp_path)
df_final = pd.read_csv(temp_path, encoding='utf-8-sig')

print(f"\n{'=' * 60}")
print(f"🎉 SELESAI! Total {len(df_final):,} data Twitter unik berhasil disimpan ke:")
print(temp_path)
if 'topic' in df_final.columns and len(df_final) > 0:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
print("=" * 60)
