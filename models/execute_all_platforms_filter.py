import os
import sys
import io
import shutil
import pandas as pd
import re
import html
import unicodedata

# Fix console encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE_DIR = os.path.join(BASE_DIR, 'ScrapeData')
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_PATH = os.path.join(BASE_DIR, 'colab_cells', 'cell_02_config.py')

PLATFORMS_TO_FILTER = ['Twitter', 'Instagram', 'TikTok', 'YouTube', 'Facebook', 'News', 'Threads']

# ==============================================================================
# 1. POLA REGEX RELEVANSI TOPIK KEMENTERIAN PEKERJAAN UMUM & MENTERI PU
# ==============================================================================

# A. MENTERI PU / MENTERI PEKERJAAN UMUM (Tokoh & Kepemimpinan)
pat_menpu_core = re.compile(
    r'\b(?:menteri[\s-]+(?:pekerjaan[\s-]+umum|pu)|menpu|wamen[\s-]+pu|wakil[\s-]+menteri[\s-]+(?:pekerjaan[\s-]+umum|pu))\b|'
    r'#\w*(?:menteripu|menteripekerjaanumum|dodyhanggodo|menpu)\w*|'
    r'\bdody[\s-]+hanggodo\b|'
    r'\bdiana[\s-]+kusumastuti\b.{0,40}(?:pu|menteri|wamen|kementerian)|'
    r'(?:pu|wamen|menteri).{0,40}\bdiana[\s-]+kusumastuti\b|'
    r'\bpak[\s-]+menteri[\s-]+pu\b|'
    r'\bmenteri[\s-]+dody\b|'
    r'(?:menteri|wamen).{0,30}(?:basuki|hadimuljono)',
    re.I
)

pat_menpu_cooccur = re.compile(
    r'(?:menteri|menpu|wamen).{0,60}(?:pekerjaan\s+umum|dody|hanggodo|diana\s+kusumastuti|komisi\s+v|sidak|kunker|tinjau\s+proyek|jalan\s+rusak|tanggul|bendungan|anggaran\s+infrastruktur)|'
    r'(?:dody\s+hanggodo|diana\s+kusumastuti).{0,60}(?:infrastruktur|jalan|jembatan|bendungan|proyek|dpr|kabinet|prabowo|kementerian|pu\b)',
    re.I
)

# B. KEMENTERIAN PEKERJAAN UMUM (Lembaga, Ditjen, Program & Proyek Infrastruktur)
pat_kemenpu_core = re.compile(
    r'\b(?:kemen[\s-]*pu|kementerian[\s-]+pekerjaan[\s-]+umum|kemenpu(?:\s*ri)?|kementerian[\s-]+pu|pu[\s-]+ri|pupr|kemenpupr|kementerian[\s-]+pupr)\b|'
    r'#\w*(?:kemenpu|kemenpuri|kementerianpekerjaanumum|pekerjaanumum|pupr|kemenpupr)\w*|'
    r'pu\.go\.id|'
    r'\bditjen[\s-]+(?:bina[\s-]+marga|sumber[\s-]+daya[\s-]+air|cipta[\s-]+karya|bina[\s-]+konstruksi)\b|'
    r'\bbina[\s-]+marga\b.{0,30}(?:pu|kementerian|jalan|jembatan)|'
    r'\bcipta[\s-]+karya\b.{0,30}(?:pu|kementerian|sanitasi|gedung)|'
    r'\bsumber[\s-]+daya[\s-]+air\b.{0,30}(?:pu|kementerian|bendungan|irigasi)|'
    r'\b(?:bbws|bbpjn)\b',
    re.I
)

pat_kemenpu_cooccur = re.compile(
    r'(?:kementerian|dinas|kantor|balai).{0,40}(?:pekerjaan\s+umum|pu\b|bina\s+marga|sda\b|cipta\s+karya)|'
    r'(?:pekerjaan\s+umum).{0,60}(?:republik\s+indonesia|ri\b|jalan\s+tol|jalan\s+nasional|jembatan|bendungan|irigasi|tanggul|banjir|infrastruktur|proyek|anggaran|tender|apbn|prabowo)|'
    r'(?:infrastruktur|proyek|preservasi\s+jalan|normalisasi\s+sungai|penanganan\s+banjir).{0,50}(?:kemen\s*pu|pu\s*ri|kementerian\s*pu)',
    re.I
)

# ==============================================================================
# 2. POLA NOISE & FILTER (TWO-TIERED ARCHITECTURE)
# ==============================================================================

# Fatal Noise: Langsung dibuang tanpa toleransi
pat_fatal_noise = re.compile(
    r"it\s+looks\s+like\s+you\s+were\s+misusing|you['’]ve\s+been\s+temporarily\s+blocked|"
    r'\b(?:slot|gacor|zeus|togel|maxwin|pragmatic|judol|judi\s+online)\b|'
    r'\b(?:forex|binomo|crypto|airdrop|binance)\b|'
    r'\b(?:bokep|open\s*bo|vcs|lendir|jav|porn)\b|'
    r'\b(?:pubg|pubgmobile|mobile\s*legends|free\s*fire|ff\s*garena)\b|'
    r'\b(?:vario|lambretta|vespa|bore\s*up|knalpot|acah2pomen)\b|'
    r'\b(?:racun\s+shopee|racun\s+tiktok|jasa\s+gestun)\b',
    re.I
)

# Context Noise: Disaring jika tidak memuat kata kunci Kementerian PU / Menteri PU inti
pat_context_noise = re.compile(
    r'\b(?:puding|resep\s*kue|brownies|dimsum|kue\s*basah)\b|'
    r'\b(?:kupu-kupu|pupuk\s*organik|puasa\s*ramadhan|bulan\s*purnama|puisi\s*cinta)\b|'
    r'\b(?:tips\s*parenting|tips\s*ibu|lagu\s*anak)\b',
    re.I
)

def run_filter_pipeline():
    print("=" * 80)
    print("MASTER DATA CLEANSING KEMEN PU RI (TWO-TIERED NOISE ARCHITECTURE)")
    print("=" * 80)

    # 1. Baca Konfigurasi Keywords dari cell_02_config.py
    print(f"Membaca konfigurasi keyword dari: {CONFIG_PATH}...")
    topics_dict = {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cfg_code = f.read()
        exec(compile(cfg_code, CONFIG_PATH, "exec"), {"__file__": CONFIG_PATH, "os": os, "re": re}, topics_dict)
        TOPICS = topics_dict.get("TOPICS", {})
        print(f"Berhasil membaca {len(TOPICS)} topik dengan total {sum(len(v) for v in TOPICS.values())} keywords.")
    except Exception as e:
        print(f"[WARN] Gagal membaca cell_02_config.py: {e}. Menggunakan konfigurasi default.")
        TOPICS = {}

    for plat in PLATFORMS_TO_FILTER:
        fname = f'scraped_{plat}_Only.csv'
        fpath = os.path.join(SCRAPE_DIR, fname)
        backup_fname = f'scraped_{plat}_Only_BEFORE_FILTER.csv'
        backup_path = os.path.join(SCRAPE_DIR, backup_fname)

        read_path = backup_path if os.path.exists(backup_path) else fpath
        if not os.path.exists(read_path):
            continue

        if not os.path.exists(backup_path) and os.path.exists(fpath):
            shutil.copy2(fpath, backup_path)
            print(f"\n[BACKUP] Menyimpan data mentah awal ke: {backup_fname}")

        try:
            df_raw = pd.read_csv(read_path, low_memory=False)
        except Exception as e:
            print(f"Gagal membaca {read_path}: {e}")
            continue

        total_raw = len(df_raw)
        col = 'content' if 'content' in df_raw.columns else 'description'
        content_raw = df_raw[col].fillna('').astype(str)

        if 'description' in df_raw.columns and 'content' in df_raw.columns:
            eval_raw = content_raw + ' ' + df_raw['description'].fillna('').astype(str)
        else:
            eval_raw = content_raw

        def normalize_text_for_eval(text):
            t = html.unescape(str(text))
            t = unicodedata.normalize('NFKD', t)
            t = re.sub(r'[\u00a0\u200b\u200c\u200d\u202f\ufeff]', ' ', t)
            return t

        eval_norm = eval_raw.apply(normalize_text_for_eval)

        match_menpu = eval_norm.str.contains(pat_menpu_core) | eval_norm.str.contains(pat_menpu_cooccur)
        match_kemenpu = eval_norm.str.contains(pat_kemenpu_core) | eval_norm.str.contains(pat_kemenpu_cooccur)
        has_any_topic = match_menpu | match_kemenpu
        has_strong_core = eval_norm.str.contains(pat_menpu_core) | eval_norm.str.contains(pat_kemenpu_core)

        hits_fatal = eval_norm.str.contains(pat_fatal_noise)
        hits_context = eval_norm.str.contains(pat_context_noise)
        hits_noise = hits_fatal | (hits_context & (~has_strong_core))

        keep_mask = has_any_topic & (~hits_noise)
        df_clean = df_raw[keep_mask].copy()

        # Update topic classification
        df_clean.loc[eval_norm.loc[df_clean.index].str.contains(pat_menpu_core), 'topic'] = 'Menteri_PU'
        df_clean.loc[~df_clean['topic'].isin(['Menteri_PU']), 'topic'] = 'Kementerian_PU'

        df_clean.to_csv(fpath, index=False, encoding='utf-8-sig')
        print(f"[{plat}] Raw: {total_raw:,} -> Bersih: {len(df_clean):,} (Dibuang: {total_raw - len(df_clean):,})")

if __name__ == '__main__':
    run_filter_pipeline()
