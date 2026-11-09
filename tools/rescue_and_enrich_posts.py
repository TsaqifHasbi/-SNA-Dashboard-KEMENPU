"""
================================================================================
🚀 RESCUE & ENRICH POSTS RUNNER (INSTAGRAM & FACEBOOK)
================================================================================
Membuka satu per satu link postingan yang:
  1. Ada di 'scraped_{platform}_Only.csv' yang caption-nya terpotong (...)
  2. Ada di 'scraped_{platform}_Kandidat_Hapus.csv' yang terbuang karena
     kata kunci terpotong saat scraping awal.

Alur Kerja:
  - Buka link postingan satu per satu via Chrome Selenium profil persisten
  - Auto-expand tombol 'more' / 'selengkapnya' / 'See more'
  - Ekstrak 100% caption lengkap dari Schema.org JSON-LD + GraphQL + Expanded DOM
  - Crosscheck: jika masih terpotong, re-click via ActionChains & reload
  - Cek relevansi topik dengan Regex Komprehensif (MBG, KDMP, Sekolah Rakyat)
  - Jika VALID:
      * Jika berasal dari Kandidat Hapus -> PINDAHKAN (RESCUE) ke CSV Utama!
      * Jika berasal dari CSV Utama -> OVERWRITE / GANTIKAN caption yang terpotong!
  - Auto-save real-time setiap 10 postingan dan saat Ctrl+C
  - Tampilkan sisa kuota yang dibutuhkan untuk mencapai 10.000 data.
================================================================================
"""

import os
import sys
import re
import time
import shutil
import argparse
import random
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

# Path direktori
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE_DIR = os.path.join(WORKSPACE_DIR, 'ScrapeData')
COLAB_DIR = os.path.join(WORKSPACE_DIR, 'colab_cells')
sys.path.insert(0, COLAB_DIR)

# Import helper modul scraping
try:
    from cell_07_instagram import enrich_single_instagram_post, IG_DRIVER
except ImportError:
    pass

try:
    from cell_09_facebook import enrich_single_facebook_post, FB_DRIVER
except ImportError:
    pass

# ==============================================================================
# REGEX FILTER RELEVANSI TOPIK KOMPREHENSIF (Mendukung Hashtag Tanpa Spasi)
# ==============================================================================
pat_mbg_core = re.compile(
    r'\bmbg\w*|'
    r'#\w*mbg\w*|'
    r'#?\w*makan(?:an)?[\s-]*bergizi[\s-]*gratis\w*|'
    r'#?\w*makan(?:an)?[\s-]*gratis[\s-]*bergizi\w*|'
    r'#?\w*makan[\s-]*siang[\s-]*gratis\w*|'
    r'#?\w*makan[\s-]*gratis[\s-]*siang\w*|'
    r'#?\w*makan[\s-]*(?:tidak|tak|bukan|gak)?[\s-]*bergizi[\s-]*(?:tidak|tak|bukan|gak)?[\s-]*gratis\w*|'
    r'makan\s*(?:\([^\)]+\)|tidak|tak|bukan|gak)\s*bergizi|'
    r'makan(?:an)?\s*bergizi\s*(?:\([^\)]+\)|tidak|tak|bukan|gak)\s*gratis|'
    r'#?\w*makan(?:an|ang)?[\s-]*gratis[\s-]*prabowo\w*|'
    r'#?\w*makan(?:an|ang)?[\s-]*gratis[\s-]*gibran\w*|'
    r'#?\w*makangratisprabowo\w*|'
    r'#?\w*makanangratisprabowo\w*|'
    r'#?\w*makangratisgibran\w*|'
    r'#?\w*makanangratisgibran\w*|'
    r'#?\w*makangratisprabowogibran\w*|'
    r'#?\w*omprengbergizi\w*|'
    r'#?\w*menumbg\w*|'
    r'#?\w*dapursppg\w*|'
    r'#?\w*badan[\s-]*gizi[\s-]*nasional\w*|'
    r'\bbgn\b|#\w*bgn\w*|'
    r'\bsppg\b|#\w*sppg\w*|'
    r'satuan\s*pelayanan\s*(?:pemenuhan\s*)?gizi|'
    r'dapur\s*(?:gizi|mbg|sehat|komunal|sppg)|'
    r'(?:prabowo|gibran).{0,60}(?:makan|mkn|gizi|susu|ompreng|bgn)|'
    r'(?:makan(?:an)?|mkn)[\s-]+gratis.{0,60}(?:prabowo|gibran|jokowi|presiden|pemerintah)',
    re.I
)

pat_mbg_cooccur = re.compile(
    r'(?:keracunan|beracun|makan(?:an)?\s+basi|makan\s+beracun).{0,250}(?:siswa|murid|guru|anak|sekolah|sd\b|smp\b|sma\b|santri|pesantren|pelajar|program|gratis|uji\s*coba|massal|katering|dapur|vendor|ompreng|korban)|'
    r'(?:siswa|murid|guru|anak|sekolah|santri|pesantren|pelajar|warga|korban).{0,250}(?:keracunan|beracun|makan(?:an)?\s+basi|makan\s+beracun)|'
    r'ompreng.{0,60}(?:makan|lauk|nasi|sayur|cuci|dapur|sekolah|anak|siswa|murid|guru|katering|program)|'
    r'susu.{0,50}(?:mbg|bgn|gratis|program|sekolah|siswa|anak|murid)|'
    r'(?:makan(?:an)?\s+bergizi.{0,70}(?:program|kebijakan|pemerintah|apbn|anggaran|alokasi|distribusi|uji\s*coba|ompreng|dapur|katering|vendor|keracunan|basi|bgn|sppg))|'
    r'(?:program|proyek|kebijakan|janji|uji\s*coba|anggaran|subsidi).{0,40}(?:makan\s+siang|makan(?:an)?\s+bergizi|makan\s+gratis|mkn\s+gratis)|'
    r'makan\s+siang.{0,50}(?:gratis|sekolah|siswa|murid|anak\s+sd|anak\s+smp|presiden|pemerintah)',
    re.I
)

pat_kdmp_core = re.compile(
    r'#?\b(?:kdmp|kdkmp|knmp)\b|'
    r'#\w*(?:kdmp|kdkmp|knmp)\w*|'
    r'#?\bagrinas\b|#\w*agrinas\w*|'
    r'#?\w*koperasidesa\w*|#?\w*koperasidesamerahputih\w*|'
    r'#?\w*koprasimerahputih\w*|'
    r'#?\w*koperasimerahputih\w*|'
    r'#?\w*koprasidesa\w*|'
    r'(?:koperasi|koprasi)[-\s]*desa[-\s]*merah[-\s]*putih|'
    r'(?:koperasi|koprasi)[-\s]*merah[-\s]*putih|'
    r'desa[-\s]*merah[-\s]*putih|'
    r'(?:koperasi|koprasi)[-\s]*desa|'
    r'kopdes[-\s]*merah[-\s]*putih|'
    r'#?\w*kopdes\b|#\w*kopdes\w*|'
    r'#?\w*manajerkopdes\w*|#?\w*managerkdmp\w*',
    re.I
)

pat_kdmp_cooccur = re.compile(
    r'(?:koperasi|koprasi|kopdes|bumdes).{0,90}(?:merah[-\s]+putih|prabowo|program|pangan|distribusi|petani|nelayan|mbg|dana\s+desa|modal|umkm|bumn|himbara|kredit|sindikasi|manajer|rekrutmen|panselnas|phtc|kemenkop|gaji\s+asn)|'
    r'kemenkop.{0,90}(?:desa|koperasi|umkm|asn|pns|pangan)|'
    r'menteri\s+koperasi|kementerian\s+koperasi|'
    r'(?:program|proyek|kebijakan|alokasi).{0,90}(?:koperasi\s+desa|desa\s+mandiri\s+pangan|kdmp|kdkmp|knmp|kopdes)',
    re.I
)

pat_sr_core = re.compile(
    r'#?\w*sekolah[-\s]*rakyat\w*|'
    r'#?\w*sekolahrakyat\w*|'
    r'#?\w*sekolah_rakyat\w*|'
    r'#?\w*sekolah[-\s]*gratis[-\s]*rakyat\w*|'
    r'#?\w*sekolah[-\s]*rakyat[-\s]*gratis\w*|'
    r'#?\w*pendidikan[-\s]*sekolah[-\s]*rakyat\w*|'
    r'#?\w*program[-\s]*sekolah[-\s]*rakyat\w*|'
    r'sekolah\s+nasional\s+terintegrasi|\bsnt\b|'
    r'sekolah\s+swasta\s+gratis|'
    r'sekolah\s+gratis\s+prabowo',
    re.I
)

pat_sr_cooccur = re.compile(
    r'(?:sekolah|pendidikan)\s+gratis.{0,80}(?:rakyat|miskin|prabowo|gibran|pemerintah|program|asta\s*cita|asrama|daerah\s+terpencil|3t\b|anggaran|apbn|swasta|negeri)|'
    r'(?:prabowo|gibran|pemerintah|presiden).{0,80}(?:sekolah\s+gratis|sekolah\s+rakyat|pendidikan\s+gratis|revitalisasi\s+sekolah)|'
    r'kemendikdasmen|mendikdasmen|'
    r'(?:abdul\s+mu\'ti|mu\'ti).{0,70}(?:sekolah|pendidikan|kurikulum|siswa|murid|guru|spp)|'
    r'sekolah\s+berasrama.{0,60}(?:gratis|rakyat|pemerintah|prabowo)|'
    r'(?:program|evaluasi|anggaran).{0,70}(?:sekolah\s+rakyat|pendidikan\s+rakyat)',
    re.I
)


# Daftar teks error dan status halaman yang bukan caption asli
BLACKLIST_ERRORS = [
    "this page isn’t working", "this page isn't working", "http error 429",
    "too many requests", "please wait a few minutes before trying again",
    "try again later", "we limit how often", "kami membatasi seberapa sering",
    "something went wrong", "sorry, this page isn't available", "halaman ini tidak tersedia",
    "redirected to instagram login", "/accounts/login", "login • instagram"
]


def norm_text(t):
    """Membersihkan whitespace dan pipe untuk perbandingan panjang teks murni."""
    if not t:
        return ""
    return re.sub(r'[\s|]+', ' ', str(t)).strip()


def is_rate_limited(details, text):
    """Mendeteksi apakah halaman terkena limit 429 atau dialihkan ke login."""
    if details.get('status') == 'RATE_LIMIT':
        return True
    t = (text or '').lower()
    phrases = [
        "this page isn’t working", "this page isn't working", "http error 429",
        "too many requests", "please wait a few minutes", "try again later",
        "we limit how often", "kami membatasi seberapa sering", "redirected to instagram login"
    ]
    return any(p in t for p in phrases)


def is_valid_caption(text):
    """Memastikan teks yang diekstrak adalah konten asli, bukan halaman error."""
    if not text:
        return False
    t = str(text).lower().strip()
    if any(err in t for err in BLACKLIST_ERRORS):
        return False
    return len(norm_text(text)) >= 3


def detect_topic(content):
    """Mendeteksi apakah sebuah teks relevan dengan MBG, KDMP, atau Sekolah Rakyat."""
    if not content or not is_valid_caption(content):
        return None
    c = str(content)
    if pat_mbg_core.search(c) or pat_mbg_cooccur.search(c):
        return "MBG"
    if pat_kdmp_core.search(c) or pat_kdmp_cooccur.search(c):
        return "KDMP"
    if pat_sr_core.search(c) or pat_sr_cooccur.search(c):
        return "Sekolah_Rakyat"
    return None


def is_caption_truncated(content):
    """Mendeteksi apakah caption benar-benar terpotong (...) atau memiliki artefak UI."""
    if not content:
        return True
    c = str(content).strip()
    if c.endswith('...') or c.endswith('…'):
        return True
    if '...' in c[-25:] or '…' in c[-25:]:
        return True
    if re.search(r'\b(more|selengkapnya|see more|lihat selengkapnya)\b', c[-40:], re.IGNORECASE):
        return True
    return False


def run_rescue_and_enrich(platform="instagram", limit=None, only_kandidat=False, only_existing=False):
    plat = platform.lower()
    assert plat in ['instagram', 'facebook'], "Platform harus 'instagram' atau 'facebook'"

    print("=" * 70)
    print(f"🚀 MEMULAI PROSES RESCUE & ENRICHMENT UNTUK {plat.upper()}")
    print("=" * 70)

    f_main = os.path.join(SCRAPE_DIR, f"scraped_{'Instagram' if plat == 'instagram' else 'Facebook'}_Only.csv")
    f_hapus = os.path.join(SCRAPE_DIR, f"scraped_{'Instagram' if plat == 'instagram' else 'Facebook'}_Kandidat_Hapus.csv")

    if not os.path.exists(f_main):
        print(f"[ERROR] File utama {f_main} tidak ditemukan!")
        return

    # Baca file utama
    try:
        df_main = pd.read_csv(f_main, encoding='utf-8-sig')
    except:
        df_main = pd.read_csv(f_main)

    df_hapus = pd.DataFrame()
    if os.path.exists(f_hapus):
        try:
            df_hapus = pd.read_csv(f_hapus, encoding='utf-8-sig')
        except:
            df_hapus = pd.read_csv(f_hapus)

    print(f"[STATUS] Data di CSV Utama: {len(df_main):,} baris")
    print(f"[STATUS] Data di Kandidat Hapus: {len(df_hapus):,} baris")

    # Buat Backup Otomatis
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_main = os.path.join(SCRAPE_DIR, f"scraped_{'Instagram' if plat == 'instagram' else 'Facebook'}_Only_BACKUP_{ts}.csv")
    df_main.to_csv(backup_main, index=False, encoding='utf-8-sig')
    print(f"[BACKUP] Backup CSV utama diamankan ke: {os.path.basename(backup_main)}")

    if not df_hapus.empty:
        backup_hapus = os.path.join(SCRAPE_DIR, f"scraped_{'Instagram' if plat == 'instagram' else 'Facebook'}_Kandidat_Hapus_BACKUP_{ts}.csv")
        df_hapus.to_csv(backup_hapus, index=False, encoding='utf-8-sig')
        print(f"[BACKUP] Backup Kandidat Hapus diamankan ke: {os.path.basename(backup_hapus)}")

    # ==========================================================================
    # 1. KUMPULKAN DAFTAR TARGET
    # ==========================================================================
    tasks = []  # List of dict: {'source': 'main'/'hapus', 'index': idx, 'url': url, 'content': content}

    # A. Dari Kandidat Hapus
    if not only_existing and not df_hapus.empty:
        for idx, row in df_hapus.iterrows():
            url = row.get('url', '')
            c = str(row.get('content', ''))
            if url and ('instagram.com' in url or 'facebook.com' in url):
                tasks.append({
                    'source': 'hapus',
                    'index': idx,
                    'url': url,
                    'content': c,
                    'row_dict': row.to_dict()
                })

    # B. Dari CSV Utama yang benar-benar terindikasi terpotong
    if not only_kandidat and not df_main.empty:
        for idx, row in df_main.iterrows():
            url = row.get('url', '')
            c = str(row.get('content', ''))
            if url and is_caption_truncated(c):
                tasks.append({
                    'source': 'main',
                    'index': idx,
                    'url': url,
                    'content': c,
                    'row_dict': row.to_dict()
                })

    print(f"\n[TARGET] Total target perbaikan & penyelamatan: {len(tasks):,} postingan")
    print(f"         - Dari Kandidat Hapus : {sum(1 for t in tasks if t['source'] == 'hapus'):,} baris")
    print(f"         - Dari CSV Utama      : {sum(1 for t in tasks if t['source'] == 'main'):,} baris")

    if limit and limit > 0:
        tasks = tasks[:limit]
        print(f"[LIMIT] Dibatasi hanya memproses {limit} postingan pertama untuk uji coba.")

    if not tasks:
        print("[OK] Tidak ada postingan yang perlu diperbaiki. Semua data sudah lengkap!")
        return

    # Inisialisasi fungsi fetcher
    fetcher = enrich_single_instagram_post if plat == 'instagram' else enrich_single_facebook_post

    rescued_count = 0
    expanded_count = 0
    hapus_indices_to_drop = []

    try:
        for step, t in enumerate(tasks, 1):
            source = t['source']
            idx = t['index']
            url = t['url']
            old_c = t['content']
            c_preview = old_c[:60].replace('\n', ' ')

            print(f"\n[{step}/{len(tasks)}] [{source.upper()}] Membuka: {url[:65]}...")
            print(f"  Old ({len(old_c)} char): '{c_preview}...'")

            details = fetcher(url)
            new_c = details.get('content', '') if plat == 'instagram' else details.get('caption', '')

            # ==================================================================
            # 🛑 INTERACTIVE PAUSE JIKA TERKENA RATE LIMIT 429 / LOGOUT
            # ==================================================================
            while is_rate_limited(details, new_c):
                print("\n" + "=" * 70)
                print("🛑 [RATE LIMIT / ERROR 429 TERDETEKSI DI INSTAGRAM!]")
                print(f"URL: {url}")
                print(f"Detail: {details.get('error', 'Akses dibatasi Instagram (This page isn\'t working / 429)')}")
                print("\n👉 TINDAKAN YANG HARUS DILAKUKAN:")
                print("1. Buka jendela Chrome Instagram yang sedang terbuka di layar Anda.")
                print("2. Silakan GANTI AKUN / LOGIN ULANG:")
                print("   - Buka https://www.instagram.com, logout akun yang terkena limit.")
                print("   - Login dengan akun Instagram Anda yang lain.")
                print("   - Pastikan beranda Instagram akun baru sudah terbuka.")
                print("3. Kembali ke terminal ini:")
                print("   - Tekan ENTER untuk mencoba ulang postingan ini dengan akun baru.")
                print("   - ATAU ketik 'exit' lalu ENTER untuk simpan data dan keluar (istirahat).")
                print("=" * 70 + "\n")

                user_inp = input("👉 Tekan ENTER jika sudah login akun baru (atau ketik 'exit'): ").strip().lower()
                if user_inp == 'exit':
                    print("\n[INFO] Proses dihentikan oleh user untuk istirahat. Menyimpan progres...")
                    raise KeyboardInterrupt

                print("🔄 Mencoba membuka ulang postingan dengan akun baru...")
                time.sleep(2)
                details = fetcher(url)
                new_c = details.get('content', '') if plat == 'instagram' else details.get('caption', '')

            # Normalisasi teks murni
            norm_old = norm_text(old_c)
            norm_new = norm_text(new_c) if new_c else ""

            # Validasi teks baru: hanya dipakai jika bukan string error blacklist
            new_valid = is_valid_caption(new_c)
            is_expanded = new_valid and (len(norm_new) > len(norm_old))

            # Tentukan teks terbaik:
            # HARAM menimpa teks lama jika teks baru tidak valid atau lebih pendek drastis
            if is_expanded:
                best_c = new_c
            elif new_valid and len(norm_new) >= len(norm_old):
                best_c = new_c
            else:
                best_c = old_c

            # Format penyimpanan standar CSV (newline -> ' | ')
            formatted_c = best_c.replace('\r', '').replace('\n', ' | ')
            formatted_c = re.sub(r'(\s*\|\s*)+', ' | ', formatted_c).strip(' |')

            # Cek Relevansi Topik
            matched_topic = detect_topic(best_c) or detect_topic(old_c)
            print(f"  [TOPIC CHECK] Hasil Analisis Relevansi: {matched_topic or 'TIDAK RELEVAN'}")

            if source == 'hapus':
                if matched_topic:
                    # RESCUE: Pindahkan dari Kandidat Hapus ke CSV Utama!
                    rescued_row = t['row_dict'].copy()
                    rescued_row['content'] = formatted_c
                    rescued_row['topic'] = matched_topic
                    if 'alasan_rekomendasi_hapus' in rescued_row:
                        del rescued_row['alasan_rekomendasi_hapus']
                    
                    if details.get('likes') and str(details['likes']).isdigit() and int(details['likes']) > rescued_row.get('likes', 0):
                        rescued_row['likes'] = int(details['likes'])

                    df_main = pd.concat([df_main, pd.DataFrame([rescued_row])], ignore_index=True)
                    hapus_indices_to_drop.append(idx)
                    rescued_count += 1
                    print(f"  ✨ [RESCUED SUCCESS] Postingan diselamatkan ke CSV Utama! (Topic: {matched_topic}, {len(norm_text(best_c))} char)")
                else:
                    print(f"  ❌ [OFF-TOPIC / DELETED] Tetap di Kandidat Hapus (Bukan topik penelitian atau halaman privat/dihapus).")
            
            elif source == 'main':
                # HANYA TIMPA CSV UTAMA JIKA TEKS BARU BENAR-BENAR LEBIH PANJANG DARI TEKS LAMA
                if is_expanded:
                    df_main.loc[idx, 'content'] = formatted_c
                    if matched_topic and df_main.loc[idx].get('topic') in ['UNKNOWN', '', None]:
                        df_main.loc[idx, 'topic'] = matched_topic
                    if details.get('likes') and str(details['likes']).isdigit() and int(details['likes']) > df_main.loc[idx].get('likes', 0):
                        df_main.loc[idx, 'likes'] = int(details['likes'])
                    expanded_count += 1
                    print(f"  ✅ [OVERWRITE SUCCESS] Data di CSV Utama berhasil diperluas ({len(norm_old)} -> {len(norm_new)} char)!")
                else:
                    print(f"  [ALREADY COMPLETE] Caption di CSV Utama sudah lengkap atau lebih panjang ({len(norm_old)} char).")

            # Checkpoint Simpan ke Disk Setiap 10 Postingan
            if step % 10 == 0:
                if 'url' in df_main.columns:
                    df_main = df_main.drop_duplicates(subset=['url'], keep='first')
                df_main.to_csv(f_main, index=False, encoding='utf-8-sig')

                if hapus_indices_to_drop and not df_hapus.empty:
                    df_hapus_cur = df_hapus.drop(index=hapus_indices_to_drop, errors='ignore')
                    df_hapus_cur.to_csv(f_hapus, index=False, encoding='utf-8-sig')

                print(f"  💾 [CHECKPOINT SAVED] ({rescued_count} diselamatkan, {expanded_count} diperluas sejauh ini).")

            time.sleep(random.uniform(1.5, 2.5))

    except KeyboardInterrupt:
        print("\n[!] Dihentikan user (Ctrl+C). Menyimpan seluruh progres...")

    finally:
        # Final Save
        if 'url' in df_main.columns:
            df_main = df_main.drop_duplicates(subset=['url'], keep='first')
        df_main.to_csv(f_main, index=False, encoding='utf-8-sig')

        if hapus_indices_to_drop and not df_hapus.empty:
            df_hapus_final = df_hapus.drop(index=hapus_indices_to_drop, errors='ignore')
            df_hapus_final.to_csv(f_hapus, index=False, encoding='utf-8-sig')

        print("\n" + "=" * 70)
        print("🎉 PROSES RESCUE & ENRICHMENT SELESAI!")
        print(f"  - Total Postingan Diselamatkan dari Kandidat Hapus : {rescued_count:,} baris")
        print(f"  - Total Postingan CSV Utama yang Diperluas        : {expanded_count:,} baris")
        print(f"  - Total Data di {os.path.basename(f_main)} Sekarang        : {len(df_main):,} baris")
        
        target_goal = 10000
        kekurangan = max(0, target_goal - len(df_main))
        if kekurangan > 0:
            print(f"\n📊 STATUS KUOTA 10.000:")
            print(f"  - Data Saat Ini  : {len(df_main):,} baris")
            print(f"  - Target         : {target_goal:,} baris")
            print(f"  - Kekurangan     : {kekurangan:,} baris lagi!")
            print(f"👉 Jalankan scraping baru untuk menutup kekurangan ini:")
            print(f"   python colab_cells/run_{plat}_only.py")
        else:
            print(f"\n🎉 TARGET TERCAPAI! Data {plat.capitalize()} sudah mencapai {len(df_main):,} baris (>= 10.000)!")
        print("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Rescue and Enrich Truncated Posts (Instagram & Facebook)")
    parser.add_argument('--platform', choices=['instagram', 'facebook'], default='instagram', help='Pilih platform')
    parser.add_argument('--limit', type=int, default=None, help='Batas jumlah post untuk diproses (opsional)')
    parser.add_argument('--only-kandidat', action='store_true', help='Hanya proses Kandidat Hapus')
    parser.add_argument('--only-existing', action='store_true', help='Hanya proses data CSV utama')
    args = parser.parse_args()

    run_rescue_and_enrich(
        platform=args.platform,
        limit=args.limit,
        only_kandidat=args.only_kandidat,
        only_existing=args.only_existing
    )
