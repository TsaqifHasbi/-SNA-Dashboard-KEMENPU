"""
MASTER URL PRIMARY KEY AUDIT & RESCUE PIPELINE (PROJECT PAK IHSAN)
==================================================================
Prinsip Utama:
1. URL adalah PRIMARY KEY (Satu-satunya dasar deduplikasi).
   - Konten yang mirip/identik dari URL berbeda TETAP DISIMPAN (KEEP).
   - Baris dengan URL yang persis sama HANYA DISISAKAN 1, duplikatnya dibuang.
2. Cross-Source Scanning:
   - Memindai 'Only.csv', 'Kandidat_Hapus.csv', 'BEFORE_FILTER.csv', dan backup lainnya.
   - RESCUE: Postingan relevan topik (MBG, KDMP, Sekolah Rakyat) yang sebelumnya
     salah masuk ke 'Kandidat_Hapus' dikembalikan ke CSV UTAMA.
   - PURGE: Postingan di CSV UTAMA yang ternyata duplikat URL atau fatal noise
     dipindahkan ke 'Kandidat_Hapus'.
"""

import os
import sys
import re
import html
import unicodedata
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE_DIR = os.path.join(BASE_DIR, 'ScrapeData')
DATA_DIR = os.path.join(BASE_DIR, 'data')
sys.path.insert(0, BASE_DIR)

from colab_cells.cell_02_config import (
    pat_mbg_core, pat_mbg_cooccur,
    pat_kdmp_core, pat_kdmp_cooccur,
    pat_sr_core, pat_sr_cooccur,
    pat_noise_filter, detect_topic
)

pat_fatal_noise = re.compile(
    r"it\s+looks\s+like\s+you\s+were\s+misusing|you['’]ve\s+been\s+temporarily\s+blocked|"
    r'pejuang\s+garis\s+dua|promil|senam\s+hamil|yoga\s+hamil|sufor|pompa\s+asi|kantung\s+asi|kantong\s+asi|usg\s+(?:2d|3d|4d)|bbj\s+janin|periksa\s+kandungan|'
    r'sekolah\s+anak\s+percaya|andien\s+aisyah|sekolah\s+koding|sekolah\s+coding|sekolah\s+forex|sekolah\s+minggu\b|'
    r'makan\s+gratis\s+rp\s*0|promo\s+ultah.{0,30}makan|syarat\s+ketentuan.{0,30}makan\s+gratis|klaim\s+promo.{0,30}makan\s+gratis|'
    r'manchester\s+united|tottenham|mbeumo|solanke|geng\s+motor|savado|'
    r'racun\s+shopee|racun\s+tiktok|jasa\s+gestun|running\s+threads|lari\s+setiap\s+hari|freedive|'
    r'kpm\s+dan\s+kkm|isu\s+jerebu|bakar\s+hutan\s+korang|menteri\s+malaysia|kerajaan\s+malaysia|sekolah\s+kebangsaan\s+rakyat|sk\s+rakyat\b|pulau\s+pinang|tarikh|timbalan|icu\s+jpm',
    re.I
)

PLATFORMS = ['Facebook', 'Instagram', 'News', 'Threads', 'TikTok', 'Twitter', 'YouTube']

def run_audit_and_rescue(target_platforms=None, dry_run=False, clean_backups=False, threads_cap=30000):
    print("=" * 80)
    mode_str = "[SIMULASI - DRY RUN]" if dry_run else "[EKSEKUSI NYATA - WRITE TO CSV]"
    print(f"🚀 MASTER AUDIT & RESCUE: URL PRIMARY KEY PIPELINE {mode_str}")
    print("=" * 80)
    
    if target_platforms is None:
        active_platforms = PLATFORMS
    elif isinstance(target_platforms, str):
        active_platforms = [p.strip() for p in target_platforms.split(',') if p.strip()]
    else:
        active_platforms = list(target_platforms)
        
    print(f"Platform target audit: {', '.join(active_platforms)}")
    
    summary_list = []
    
    for plat in active_platforms:
        f_only = os.path.join(SCRAPE_DIR, f"scraped_{plat}_Only.csv")
        f_hapus = os.path.join(SCRAPE_DIR, f"scraped_{plat}_Kandidat_Hapus.csv")
        
        dfs = []
        if os.path.exists(f_only):
            d1 = pd.read_csv(f_only, low_memory=False)
            d1['_source_tag'] = '1_Only'
            dfs.append(d1)
        if os.path.exists(f_hapus):
            d2 = pd.read_csv(f_hapus, low_memory=False)
            d2['_source_tag'] = '2_Kandidat_Hapus'
            dfs.append(d2)
            
        # Pindai SEMUA file backup yang ada untuk platform ini agar tidak ada data yang tertinggal
        import glob
        all_backup_files = [f for f in glob.glob(os.path.join(SCRAPE_DIR, f"*{plat}*.csv"))
                            if f != f_only and f != f_hapus]
        for idx_b, f_bak_path in enumerate(all_backup_files):
            try:
                dbk = pd.read_csv(f_bak_path, low_memory=False)
                dbk['_source_tag'] = f'3_Backup_{idx_b}'
                dfs.append(dbk)
            except Exception as e:
                print(f"  [WARN] Gagal membaca {os.path.basename(f_bak_path)}: {e}")
                
        if not dfs:
            print(f"⚠️ Melewati {plat}: File dataset tidak ditemukan.")
            continue
            
        combined = pd.concat(dfs, ignore_index=True)
        raw_count = len(combined)
        
        # Kolom teks
        col = 'content' if 'content' in combined.columns else 'description'
        eval_t = combined[col].fillna('').astype(str).str.strip()
        if 'description' in combined.columns and col != 'description':
            eval_t = eval_t + ' ' + combined['description'].fillna('').astype(str).str.strip()
            
        # Normalisasi Unicode font (NFKD) agar font italic/bold matematik tetap dikenali regex
        combined['eval_text'] = eval_t.apply(lambda s: unicodedata.normalize('NFKD', s) if s else '')
            
        # Bersihkan URL
        combined['url_clean'] = combined['url'].fillna('').astype(str).str.strip()
        
        # 1. Masking Topik & Noise
        txt = combined['eval_text']
        m_mbg = txt.str.contains(pat_mbg_core) | txt.str.contains(pat_mbg_cooccur)
        m_kdmp = txt.str.contains(pat_kdmp_core) | txt.str.contains(pat_kdmp_cooccur)
        m_sr = txt.str.contains(pat_sr_core) | txt.str.contains(pat_sr_cooccur)
        m_topic = m_mbg | m_kdmp | m_sr
        m_fatal = txt.str.contains(pat_fatal_noise)
        m_short = txt.str.len() < 12
        
        # Penentuan topik terakreditasi
        assigned_topic = combined['topic'].copy() if 'topic' in combined.columns else pd.Series('MBG', index=combined.index)
        assigned_topic[m_mbg & (~m_kdmp) & (~m_sr)] = 'MBG'
        assigned_topic[m_kdmp & (~m_mbg) & (~m_sr)] = 'KDMP'
        assigned_topic[m_sr & (~m_mbg) & (~m_kdmp)] = 'Sekolah_Rakyat'
        combined['topic'] = assigned_topic
        
        valid_relevance = m_topic & (~m_fatal) & (~m_short)
        
        # Prioritas pemilahan: Baris dari 'Only' dinilai lebih dulu
        combined.sort_values(by=['_source_tag'], ascending=True, inplace=True)
        
        # Pisahkan yang relevan dan non-relevan
        rel_df = combined[valid_relevance].copy()
        non_rel_df = combined[~valid_relevance].copy()
        non_rel_df['alasan_rekomendasi_hapus'] = 'Out of Topic / Fatal Noise / Teks Terlalu Pendek'
        
        # 2. DEDUPLIKASI BERBASIS URL MURNI (URL Primary Key)
        # Pisahkan baris yang punya URL vs tidak punya URL
        has_url = (rel_df['url_clean'] != '') & (rel_df['url_clean'] != 'nan')
        
        # Unique URL -> KEEP
        clean_url_kept = rel_df[has_url].drop_duplicates(subset=['url_clean'], keep='first')
        
        # Duplicate URL -> BUANG (Pindahkan ke kandidat hapus)
        dup_url_mask = rel_df[has_url].duplicated(subset=['url_clean'], keep='first')
        dup_url_df = rel_df[has_url][dup_url_mask].copy()
        dup_url_df['alasan_rekomendasi_hapus'] = 'Duplikat URL (Sudah ada di dataset utama)'
        
        no_url_kept = rel_df[~has_url]
        
        # Gabungkan data KEEP final
        final_clean = pd.concat([clean_url_kept, no_url_kept], ignore_index=True)
        
        # Gabungkan data DISCARD final
        final_discard = pd.concat([non_rel_df, dup_url_df], ignore_index=True)
        if 'url_clean' in final_discard.columns:
            has_url_d = (final_discard['url_clean'] != '') & (final_discard['url_clean'] != 'nan')
            d_url = final_discard[has_url_d].drop_duplicates(subset=['url_clean'], keep='first')
            d_no_url = final_discard[~has_url_d].drop_duplicates(subset=['eval_text'], keep='first')
            final_discard = pd.concat([d_url, d_no_url], ignore_index=True)
        
        # Hitung statistik sebelum capping Threads
        uncapped_clean_cnt = len(final_clean)
        
        # 3. PERLAKUAN KHUSUS THREADS: CAPPING 30K + FULL ARCHIVE 162K
        if plat == 'Threads' and threads_cap and uncapped_clean_cnt > threads_cap:
            f_full_threads = os.path.join(SCRAPE_DIR, "scraped_Threads_Only_FULL_162K.csv")
            if not dry_run:
                cols_drop = ['_source_tag', 'eval_text', 'url_clean', 'alasan_rekomendasi_hapus']
                full_save = final_clean.drop(columns=[c for c in cols_drop if c in final_clean.columns])
                full_save.to_csv(f_full_threads, index=False, encoding='utf-8')
                print(f"  [ARCHIVE FULL] Menyimpan {len(full_save):,} baris Threads lengkap ke {os.path.basename(f_full_threads)}")
            
            # Capping 30.000 berimbang antar 3 topik (MBG, KDMP, Sekolah_Rakyat)
            target_per_topic = threads_cap // 3
            sampled_dfs = []
            for top in ['MBG', 'KDMP', 'Sekolah_Rakyat']:
                df_top = final_clean[final_clean['topic'] == top]
                if len(df_top) > target_per_topic:
                    sampled_dfs.append(df_top.sample(n=target_per_topic, random_state=42))
                else:
                    sampled_dfs.append(df_top)
            
            capped_df = pd.concat(sampled_dfs, ignore_index=True)
            if len(capped_df) < threads_cap and len(final_clean) > len(capped_df):
                rem_needed = threads_cap - len(capped_df)
                unused = final_clean[~final_clean.index.isin(capped_df.index)]
                fill_df = unused.sample(n=min(rem_needed, len(unused)), random_state=42)
                capped_df = pd.concat([capped_df, fill_df], ignore_index=True)
            
            final_clean = capped_df
            print(f"  [CAPPED THREADS] Dicapping ke {len(final_clean):,} baris seimbang (10k MBG, 10k KDMP, 10k SR). Master {uncapped_clean_cnt:,} aman diarsipkan.")

        # Hitung statistik
        cur_only_cnt = len(d1) if os.path.exists(f_only) else 0
        rescued_from_hapus = (final_clean['_source_tag'] == '2_Kandidat_Hapus').sum()
        rescued_from_bak = (final_clean['_source_tag'].str.startswith('3_Backup')).sum()
        total_rescued = rescued_from_hapus + rescued_from_bak
        purged_from_only = (final_discard['_source_tag'] == '1_Only').sum()
        
        summary_list.append({
            'Platform': plat,
            'Sebelumnya': cur_only_cnt,
            'Setelah_Clean': len(final_clean),
            'Diselamatkan (+Rekup)': total_rescued,
            'Dibuang_dari_Utama (-Purge)': purged_from_only,
            'Total_Kandidat_Hapus': len(final_discard),
            'Net_Kenaikan': len(final_clean) - cur_only_cnt
        })
        
        # Eksekusi Write jika bukan dry_run
        if not dry_run:
            # Backup file lama sebelum overwrite
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if os.path.exists(f_only):
                f_only_bak = os.path.join(SCRAPE_DIR, f"scraped_{plat}_Only_PRE_AUDIT_{ts}.csv")
                pd.read_csv(f_only, low_memory=False).to_csv(f_only_bak, index=False, encoding='utf-8')
            
            # Bersihkan metadata internal sebelum simpan
            cols_to_drop_clean = ['_source_tag', 'eval_text', 'url_clean', 'alasan_rekomendasi_hapus']
            cols_to_drop_discard = ['_source_tag', 'eval_text', 'url_clean']
            final_clean_save = final_clean.drop(columns=[c for c in cols_to_drop_clean if c in final_clean.columns])
            final_discard_save = final_discard.drop(columns=[c for c in cols_to_drop_discard if c in final_discard.columns])
            
            final_clean_save.to_csv(f_only, index=False, encoding='utf-8')
            final_discard_save.to_csv(f_hapus, index=False, encoding='utf-8')
            print(f"  [SAVED] {plat}: {len(final_clean_save):,} baris ke {os.path.basename(f_only)} | {len(final_discard_save):,} ke {os.path.basename(f_hapus)}")
            
            # Hapus file backup sementara jika diminta (TIDAK menghapus file ORIGINAL_148K atau PRE_AUDIT)
            if clean_backups:
                safe_del = [f for f in all_backup_files if 'ORIGINAL' not in f and 'PRE_AUDIT' not in f and 'FULL_162K' not in f]
                for f_del in safe_del:
                    try:
                        if os.path.exists(f_del):
                            os.remove(f_del)
                            print(f"  [DELETED BACKUP] Menghapus {os.path.basename(f_del)}")
                    except Exception as e:
                        print(f"  [WARN] Gagal menghapus {os.path.basename(f_del)}: {e}")
            
    summary_df = pd.DataFrame(summary_list)
    print("\n" + summary_df.to_string(index=False))
    print("=" * 80)
    print(f"Total Data Bersih Utama : {summary_df['Sebelumnya'].sum():,} -> {summary_df['Setelah_Clean'].sum():,} baris")
    print(f"Net Data Tambahan       : +{summary_df['Net_Kenaikan'].sum():,} baris")
    print("=" * 80)
    return summary_df

if __name__ == '__main__':
    is_dry = '--dry-run' in sys.argv
    clean_bak = '--clean-backups' in sys.argv or '--delete-backups' in sys.argv
    
    # Deteksi argumen platform opsional & threads cap
    plat_arg = None
    threads_cap_val = 30000
    for idx, arg in enumerate(sys.argv):
        if arg == '--platform' and idx + 1 < len(sys.argv):
            plat_arg = sys.argv[idx + 1]
        elif arg.startswith('--platform='):
            plat_arg = arg.split('=', 1)[1]
        elif arg == '--threads-cap' and idx + 1 < len(sys.argv):
            threads_cap_val = int(sys.argv[idx + 1])
        elif arg.startswith('--threads-cap='):
            threads_cap_val = int(arg.split('=', 1)[1])
        elif arg == '--no-threads-cap':
            threads_cap_val = None
            
    run_audit_and_rescue(target_platforms=plat_arg, dry_run=is_dry, clean_backups=clean_bak, threads_cap=threads_cap_val)

