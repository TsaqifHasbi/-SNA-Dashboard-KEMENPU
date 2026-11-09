import os
import sys

# Fix Windows console encoding SEBELUM import apapun (cell_02_config mencetak emoji)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import random
import shutil
import pandas as pd
from cell_02_config import TOPICS, OUTPUT_DIR
from cell_05_tiktok import scrape_tiktok, load_seen_urls, reset_tracking, TIKTOK_PROFILE_DIR

# ========== OPSI FRESH LOGIN / RELOGIN ==========
if '--relogin' in sys.argv or '--fresh-login' in sys.argv:
    if os.path.exists(TIKTOK_PROFILE_DIR):
        try:
            shutil.rmtree(TIKTOK_PROFILE_DIR, ignore_errors=True)
            print("[🔄] Flag --relogin aktif: Session/cookies TikTok lama sudah dihapus.")
        except Exception as e:
            print(f"[WARN] Gagal hapus session lama: {e}")
elif os.path.exists(TIKTOK_PROFILE_DIR):
    print("[INFO] Menggunakan sesi login TikTok yang tersimpan.")
    print("       (Tambahkan flag --relogin jika Anda ingin ganti akun TikTok baru)")
else:
    print("[INFO] Belum ada sesi TikTok tersimpan. Akan meminta login baru.")

print("=" * 60)
print("🚀 MEMULAI SCRAPING TIKTOK ONLY")
print("📊 Target Quota:")
print("   - 2 Keyword Utama per Topik : 1000 data")
print("   - Keyword Sisanya           : 100 data")
print("🔄 Auto-Resume: Aktif (skip keyword yang sudah selesai)")
print("💾 Auto-Save  : Langsung tersimpan ke CSV setiap 1 keyword selesai")
print("=" * 60)

all_results = []
total_keywords = sum(len(kws) for kws in TOPICS.values())
current_kw = 1

temp_path = os.path.join(OUTPUT_DIR, "scraped_TikTok_Only.csv")
keyword_counts = {}

# AUTO-RESUME: Cek CSV yang sudah ada
if os.path.exists(temp_path):
    try:
        try:
            df_existing = pd.read_csv(temp_path, encoding='utf-8-sig')
        except Exception:
            df_existing = pd.read_csv(temp_path)

        if 'keyword' in df_existing.columns:
            keyword_counts = df_existing['keyword'].value_counts().to_dict()
        all_results = df_existing.to_dict('records')

        # Load existing URLs untuk deduplikasi global
        if 'url' in df_existing.columns:
            existing_urls = set(df_existing['url'].dropna().unique())
            load_seen_urls(existing_urls)

        print(f"[INFO] Melanjutkan dari file yang ada!")
        print(f"       - {len(keyword_counts)} keyword terdaftar di CSV")
        print(f"       - {len(all_results)} data sudah tersimpan di CSV")
    except Exception as e:
        print(f"[WARN] Gagal membaca CSV lama: {e}")
        reset_tracking()
else:
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
        # 2 keyword utama target 1000 data, sisanya 100 data
        target_results = 10000 if i == 0 else 1000
        current_count = keyword_counts.get(kw, 0)

        # 1. CEK APAKAH SUDAH MEMENUHI TARGET
        if current_count >= target_results:
            print(f"  [{current_kw}/{total_keywords}] [SKIP] Keyword '{kw}' sudah terpenuhi ({current_count}/{target_results} data).")
            current_kw += 1
            continue

        # 2. HITUNG SISA KEKURANGAN
        needed = target_results - current_count
        if current_count > 0:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Sudah ada: {current_count}/{target_results} | Mencari sisa: {needed} data baru)")
        else:
            print(f"\n  [{current_kw}/{total_keywords}] Keyword: '{kw}' (Target: {target_results} data | Belum ada data di CSV)")

        try:
            data = scrape_tiktok(kw, max_results=needed)

            for d in data:
                d['topic'] = topic

            all_results.extend(data)

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
            cols_order = ['platform', 'topic', 'content', 'author', 'handle', 'url', 'views', 'likes', 'comments', 'shares', 'saves', 'created_at', 'keyword', 'scraped_at']
            ordered = [c for c in cols_order if c in df_temp.columns] + [c for c in df_temp.columns if c not in cols_order]
            df_temp = df_temp[ordered]

            df_temp.to_csv(temp_path, index=False, encoding='utf-8-sig')
            if 'keyword' in df_temp.columns:
                keyword_counts = df_temp['keyword'].value_counts().to_dict()
            print(f"  [OK] Tersimpan! Total data di CSV: {len(df_temp)} (Keyword '{kw}': {keyword_counts.get(kw, 0)}/{target_results})")

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
            print("  [INFO] Jalankan ulang script ini kapan saja untuk melanjutkan (auto-resume).")
            sys.exit(0)

        except Exception as e:
            print(f"  [ERROR] Scraping gagal/terputus pada keyword '{kw}': {e}")
            if all_results:
                df_save = pd.DataFrame(all_results)
                df_save.to_csv(temp_path, index=False, encoding='utf-8-sig')
                print(f"  [SAVE] Data tersimpan ({len(df_save)} baris) sebelum recovery.")

            print("  [INFO] Merestart Chrome untuk keyword berikutnya...")
            import cell_05_tiktok
            try:
                if cell_05_tiktok.TIKTOK_DRIVER is not None:
                    cell_05_tiktok.TIKTOK_DRIVER.quit()
            except Exception:
                pass
            cell_05_tiktok.TIKTOK_DRIVER = None
            cell_05_tiktok._kill_zombie_chrome_tiktok()
            time.sleep(3)

        current_kw += 1

        # --- COOLDOWN ANTAR KEYWORD: Anti Rate-Limit ---
        # Jeda 30-60 detik antar keyword agar TikTok tidak mendeteksi bot
        if current_kw <= total_keywords:
            cooldown = random.uniform(30, 60)
            # Setiap 10 keyword, istirahat lebih lama (2-3 menit)
            if (current_kw - 1) % 10 == 0:
                cooldown = random.uniform(120, 180)
                print(f"  [⏳] Istirahat panjang {cooldown:.0f} detik (setiap 10 keyword) untuk hindari rate-limit...")
            else:
                print(f"  [⏳] Jeda {cooldown:.0f} detik sebelum keyword berikutnya...")
            time.sleep(cooldown)

# Final dedup & save
df_final = pd.DataFrame(all_results)
if 'url' in df_final.columns and len(df_final) > 0:
    mask_has_url = df_final['url'].notna() & (df_final['url'] != '')
    df_with_url = df_final[mask_has_url].drop_duplicates(subset=['url'], keep='first')
    df_no_url = df_final[~mask_has_url]
    df_final = pd.concat([df_with_url, df_no_url], ignore_index=True)
df_final.to_csv(temp_path, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"🎉 SELESAI! Total {len(df_final)} data TikTok unik berhasil disimpan ke:")
print(temp_path)
if 'topic' in df_final.columns and len(df_final) > 0:
    print(f"\nDistribusi topik:")
    print(df_final['topic'].value_counts().to_string())
print("=" * 60)
