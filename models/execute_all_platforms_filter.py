import os
import sys
import io
import shutil
import pandas as pd
import re
import html
import unicodedata
import urllib.parse


def canonicalize_url(u):
    """
    Normalisasi & ekstraksi URL kanonik lintas platform:
    1. Membuka pembungkus redirector Bing News (apiclick.aspx?...&url=...) & Google (google.com/url?q=...)
    2. Menyatukan alias skema & domain (http->https, twitter.com->x.com, threads.net->threads.com, m.facebook->www.facebook)
    3. Menghapus parameter pelacak acak (tid, aid, utm_*, fbclid, igsh, xmt, dll) tanpa merusak ID postingan asli (v, fbid, story_fbid, id).
    """
    if u is None or (isinstance(u, float) and pd.isna(u)):
        return ""
    s = str(u).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""

    # 1. Buka pembungkus redirector Bing News RSS
    if "bing.com/news/apiclick.aspx" in s.lower():
        try:
            parsed = urllib.parse.urlparse(s)
            qs = urllib.parse.parse_qs(parsed.query)
            if "url" in qs and qs["url"]:
                s = urllib.parse.unquote(qs["url"][0]).strip()
        except Exception:
            pass

    # 2. Buka pembungkus redirector Google URL
    if "google.com/url?" in s.lower():
        try:
            parsed = urllib.parse.urlparse(s)
            qs = urllib.parse.parse_qs(parsed.query)
            for k in ("q", "url"):
                if k in qs and qs[k]:
                    s = urllib.parse.unquote(qs[k][0]).strip()
                    break
        except Exception:
            pass

    # 3. Normalisasi protokol & domain alias sosial media
    s = re.sub(r"^http://", "https://", s, flags=re.I)
    s = re.sub(r"^https://(?:www\.|mobile\.|m\.)?(?:twitter\.com|x\.com)/", "https://x.com/", s, flags=re.I)
    s = re.sub(r"^https://(?:m\.|web\.|mobile\.)?facebook\.com/", "https://www.facebook.com/", s, flags=re.I)
    s = re.sub(r"^https://(?:www\.)?threads\.net/", "https://www.threads.com/", s, flags=re.I)

    # 4. Bersihkan query parameter tracking acak namun pertahankan parameter identitas konten
    try:
        p = urllib.parse.urlparse(s)
        if p.scheme and p.netloc:
            keep_keys = {"v", "fbid", "story_fbid", "id", "p", "article_id", "read"}
            drop_prefixes = (
                "utm_", "ref", "tid", "aid", "mkt", "fbclid", "gclid", "igsh",
                "xmt", "__cft__", "__tn__", "oc", "ved", "usg", "hl", "gl", "ceid"
            )
            drop_exact = {"s", "t", "c", "src", "amp"}
            if p.query:
                qs_pairs = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
                filtered_pairs = [
                    (k, v) for (k, v) in qs_pairs
                    if not (k.lower() == "page" and v.strip().lower() in ("all", "1"))
                    and (
                        k.lower() in keep_keys
                        or k.lower() == "page"
                        or (not k.lower().startswith(drop_prefixes) and k.lower() not in drop_exact)
                    )
                ]
                new_q = urllib.parse.urlencode(sorted(filtered_pairs))
            else:
                new_q = ""
            clean_path = p.path.rstrip("/") if p.path != "/" else ""
            s = urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), clean_path, "", new_q, ""))
    except Exception:
        s = s.rstrip("/")

    return s

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
    r'\b(?:ment(?:eri|ri)[\s-]+(?:pekerjaan[\s-]+umum|pu(?:\w*))|menpu|wamen[\s-]+pu|wakil[\s-]+menteri[\s-]+(?:pekerjaan[\s-]+umum|pu))\b|'
    r'#\w*(?:menteripu|menteripekerjaanumum|dodyhanggodo|menpu)\w*|'
    r'\bdod+y[\s-]+hanggodo\b|'
    r'\b(?:menteri|mentri)[\s-]+dod+y\b|'
    r'\bdiana[\s-]+kusumastuti\b.{0,40}(?:pu|menteri|wamen|kementerian|kementrian)|'
    r'(?:pu|wamen|menteri|mentri).{0,40}\bdiana[\s-]+kusumastuti\b|'
    r'\bpak[\s-]+ment(?:eri|ri)[\s-]+pu\b|'
    r'(?:ment(?:eri|ri)|wamen).{0,30}(?:basuki|hadimuljono)',
    re.I
)

pat_menpu_cooccur = re.compile(
    r'(?:ment(?:eri|ri)|menpu|wamen).{0,60}(?:pekerjaan\s+umum|dod+y|hanggodo|diana\s+kusumastuti|komisi\s+v|sidak|kunker|tinjau\s+proyek|jalan\s+rusak|tanggul|bendungan|anggaran\s+infrastruktur)|'
    r'(?:dod+y\s+hanggodo|diana\s+kusumastuti).{0,60}(?:infrastruktur|jalan|jembatan|bendungan|proyek|dpr|kabinet|prabowo|kementerian|kementrian|\bpu\b)',
    re.I
)

# B. KEMENTERIAN PEKERJAAN UMUM (Lembaga, Ditjen, Balai Vertikal, Program & Proyek Infrastruktur)
pat_kemenpu_core = re.compile(
    r'\b(?:kemen[\s-]*pu(?:pr)?(?:\w*)|kement(?:eri|ri)an[\s-]+pekerjaan[\s-]+umum(?:\s+republik\s+indonesia|\s+ri)?|kemenpu(?:pr)?(?:\w*)|kement(?:eri|ri)an[\s-]+pu(?:pr)?(?:\s*ri)?|pu[\s-]+ri|pupr|kemenpupr)\b|'
    r'\b(?:departemen|sektor|instansi|lingkup|bidang|kantor)[\s-]*pekerjaan[\s-]+umum\b|'
    r'#\w*(?:kemenpu|kemenpuri|kementerianpu|kementrianpu|kementerianpekerjaanumum|kementrianpekerjaanumum|pekerjaanumum|pupr|kemenpupr|bpsdmpu)\w*|'
    r'@\w*(?:kemenpu|kemenpu_|pupr|pekerjaanumum|binamarga|ciptakarya)\w*|'
    r'pu\.go\.id|'
    r'\b(?:politeknik[\s-]+pekerjaan[\s-]+umum|politeknik[\s-]+pu)\b|'
    r'\bditjen[\s-]+(?:bina[\s-]+marga|sumber[\s-]+daya[\s-]+air|cipta[\s-]+karya|bina[\s-]+konstruksi|pembiayaan[\s-]+infrastruktur)\b|'
    r'\bbina[\s-]+marga\b.{0,30}(?:pu|kementerian|kementrian|jalan|jembatan)|'
    r'\bcipta[\s-]+karya\b.{0,30}(?:pu|kementerian|kementrian|sanitasi|gedung)|'
    r'\bsumber[\s-]+daya[\s-]+air\b.{0,30}(?:pu|kementerian|kementrian|bendungan|irigasi)|'
    r'\b(?:balai[\s-]+besar|balai)[\s-]+(?:wilayah[\s-]+sungai|pelaksanaan[\s-]+jalan|pengelolaan[\s-]+jalan|prasarana[\s-]+permukiman|jasa[\s-]+konstruksi|teknologi|penelitian|jalan|sungai|ciliwung|bengawan[\s-]+solo|brantas|citarum|pemali[\s-]+juana|citanduy|mesuji|serayu|sadang|pompengan|jeenelata|teras|kalimantan|sumatera|papua|sulawesi|bali|lombok|ntt|ntb)\b|'
    r'\b(?:bbws|bws|bbpjn|bpjn|bpsdm[\s-]+pu|bp2jk|bppw)\b',
    re.I
)

pat_kemenpu_cooccur = re.compile(
    r'(?:kementerian|kementrian|kantor|balai).{0,40}(?:pekerjaan\s+umum|\bpu\b|bina\s+marga|sda\b|cipta\s+karya)|'
    r'(?:pegawai|asn|pejabat|staf|inspektorat|di\s+lingkungan|internal|vendor|orang).{0,25}(?:kemen[\s-]*pu|\bpu\b|\bpupr\b|pekerjaan\s+umum)|'
    r'(?:pekerjaan\s+umum).{0,60}(?:republik\s+indonesia|ri\b|jalan\s+tol|jalan\s+nasional|jembatan|bendungan|irigasi|tanggul|banjir|infrastruktur|proyek|anggaran|tender|apbn|prabowo|tenaga)|'
    r'(?:infrastruktur|proyek|preservasi\s+jalan|normalisasi\s+sungai|penanganan\s+banjir).{0,50}(?:kemen\s*pu|pu\s*ri|kementerian\s*pu|kementrian\s*pu)',
    re.I
)

# C. ATURAN KHUSUS DINAS PEMDA VS BALAI VERTIKAL
# Dinas PU Pemda (Kabupaten/Kota/Provinsi) murni di-takeout jika tanpa konteks Kementerian PU / Balai vertikal
pat_dinas_pemda_only = re.compile(
    r'\b(?:dinas[\s-]+pu(?:pr)?|dpupr|dputr|kadis[\s-]+pu(?:pr)?|dinas[\s-]+pekerjaan[\s-]+umum)\b',
    re.I
)
pat_vertikal_pu = re.compile(
    r'\b(?:kemen[\s-]*pu(?:pr)?|kement(?:eri|ri)an[\s-]+(?:pu(?:pr)?|pekerjaan[\s-]+umum)|'
    r'ment(?:eri|ri)[\s-]+(?:pu(?:pr)?|pekerjaan[\s-]+umum|dody)|wamen[\s-]+pu|'
    r'dody[\s-]+hanggodo|hanggodo|basuki[\s-]+hadimuljono|diana[\s-]+kusumastuti|lomba\s+kementerian\s+pu|'
    r'balai[\s-]+(?:besar|pelaksanaan|wilayah|pengelolaan|prasarana|jasa|teknik)|'
    r'bbws|bws|bbpjn|bpjn|bp2jk|bppw|bina\s+marga\s+kementerian|'
    r'pu_(?:jalan|sda|ciptakarya|bpsdm|bjkw|binamarga|prasaranastrategis)|'
    r'ditjen[\s-]+(?:bina[\s-]+marga|sumber[\s-]+daya[\s-]+air|cipta[\s-]+karya|bina[\s-]+konstruksi|prasarana)|'
    r'inpres[\s-]+jalan[\s-]+daerah|\bijd\b|apbn)\b',
    re.I
)

# ==============================================================================
# 2. POLA NOISE & FILTER (TWO-TIERED ARCHITECTURE)
# ==============================================================================

# Fatal Noise: Langsung dibuang tanpa toleransi (Spam Iklan Judi/Slot, Dewasa, Game, Otomotif, Promo E-commerce)
# CATATAN: 'judol' / 'judi online' TIDAK dimasukkan ke fatal noise agar berita/diskusi penindakan disiplin ASN KemenPU tidak terbuang.
# CATATAN: 'depo' dibatasi pada pola transaksi judi (depo pulsa/dana/qris/10k) agar depo air bersih / depo tanggap darurat PU tidak terbuang.
pat_fatal_noise = re.compile(
    r"it\s+looks\s+like\s+you\s+were\s+misusing|you['’]ve\s+been\s+temporarily\s+blocked|"
    r'\b(?:slot|gacor|zeus|togel|maxwin|pragmatic|scatter|free\s*spin|jackpot|rtp\s*slot|situs\s*judi|agen\s*judi|link\s*gacor)\b|'
    r'\b(?:depo\s*(?:wd|pulsa|dana|qris|\d+k)|min(?:imal)?\s*depo)\b|'
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

        # Kanonikalisasi & deduplikasi URL (membuka bungkus Bing apiclick & tracking query)
        if 'url' in df_clean.columns:
            df_clean['url'] = df_clean['url'].apply(canonicalize_url)
            has_u = df_clean['url'] != ''
            df_clean = pd.concat([
                df_clean[has_u].drop_duplicates(subset=['url'], keep='first'),
                df_clean[~has_u]
            ], ignore_index=True)

        # Update topic classification
        df_clean.loc[eval_norm.loc[df_clean.index].str.contains(pat_menpu_core), 'topic'] = 'Menteri_PU'
        df_clean.loc[~df_clean['topic'].isin(['Menteri_PU']), 'topic'] = 'Kementerian_PU'

        df_clean.to_csv(fpath, index=False, encoding='utf-8-sig')
        print(f"[{plat}] Raw: {total_raw:,} -> Bersih: {len(df_clean):,} (Dibuang: {total_raw - len(df_clean):,})")

if __name__ == '__main__':
    run_filter_pipeline()
