# ============================================================
# CELL 2: KONFIGURASI KREDENSIAL & TOPIK PENELITIAN KEMEN PU
# Objek Penelitian: 
#   1. Kementerian Pekerjaan Umum (Kemen PU RI / Kementerian Pekerjaan Umum Republik Indonesia)
#   2. Menteri PU / Menteri Pekerjaan Umum (Ir. Dody Hanggodo, M.P.E. & Jajaran)
# Model Analisis : IndoBERT Sentiment Analysis & Social Network Analysis (SNA)
# ============================================================

import os
import sys
import re

# Fix Windows console encoding for emoji printing
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# pyrefly: ignore [missing-import]
import nest_asyncio
nest_asyncio.apply()

# ================================================================
# DIREKTORI OUTPUT (Path Lokal Windows)
# ================================================================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ScrapeData')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load environment variables dari .env (jika ada)
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except Exception:
    pass

# ================================================================
# YOUTUBE — YouTube Data API v3 Key (Multi-Key Rotation dari .env)
# ================================================================
_yt_env_keys = os.environ.get('YOUTUBE_API_KEYS', '')
if _yt_env_keys:
    YOUTUBE_API_KEYS = [k.strip() for k in _yt_env_keys.split(',') if k.strip()]
else:
    YOUTUBE_API_KEYS = [k for k in [
        os.environ.get('YOUTUBE_API_KEY'),
        os.environ.get('YOUTUBE_API_KEY_2'),
        os.environ.get('YOUTUBE_API_KEY_3'),
    ] if k and k.strip()]

YOUTUBE_API_KEY = YOUTUBE_API_KEYS[0] if YOUTUBE_API_KEYS else os.environ.get('YOUTUBE_API_KEY', 'YOUR_YOUTUBE_API_KEY_HERE')

# ================================================================
# TWITTER/X — Cookie dari browser
# ================================================================
TWITTER_COOKIES = {
    "auth_token": "687912004832a6234b5abcd93fad043ea267297d",
    "ct0": "1511710ab6133140b5e53033eb304ac563dda9643151557a41b65f4dee289a7b2fc9ec94e2da88946013d2bd7057caf05b49529a737d9075145d13b8c8b780473ffae48c74767babde6460cf7a8dc091",
}

# ================================================================
# TIKTOK — Cookie dari browser
# ================================================================
TIKTOK_COOKIE = """delay_guest_mode_vid=5; g_state={"i_l":0,"i_ll":1782032495741,"i_b":"dBXb7unjIx9Yrqv6ZRXqzjduVh77FIgS/z1kLpU5RJU","i_e":{"enable_itp_optimization":24},"i_et":1782032495741}; last_login_method=google; _ttp=3Fkw4wHiesRWMah2CKvIPiWWeLH; passport_csrf_token=ad93fec592e3e1a3988700f04a58adfe; passport_csrf_token_default=ad93fec592e3e1a3988700f04a58adfe; myCookie=rap; s_v_web_id=verify_mudom0wp_e0oSJ2sB_XfHU_4S1S_9UoK_f6SGhQdpFwko; tiktok_webapp_theme_source=auto; tiktok_webapp_theme=dark; tt_ticket_guard_has_set_public_key=1; passport_fe_beating_status=true; waforiginalreid=https://www.tiktok.com/; waforigin_id=44; _waftokenid=eyJ2Ijp7ImEiOiIvRWswQ1JLdytYU092T3hEbnFOQktwQWhkdTFOMVRvSkFiYXVrVW5UVExZPSIsImIiOjE3OTA2MTE1MDUsImMiOiJYb3BrY3llWkU0RHM2aWVycm44dGdhNi96TG9iL245aG1mamJoc2orbENJPSJ9LCJzIjoiU0ZuZHVYM1pUeEJEUWlkVkY5eW5XU0F3ZjNOQVozYXlVNjZzekQxbCtGYz0ifQ; msToken=8Dwa7OAKeUeAG3S7OZxhHAvdTUqJWMt7A-rRWdcOTk5_5VrYulMwcV7WcQNIvUVHMiZPv5agmLIhRxXoFn_gB4Ru8jtRZqTvk8j9mWvNqeXBOIGIxs_3npUINIXRK-R26KvMwxyGmcIEfU4mGeUdGqMA7hrlAoo4dbcANmVrPzI=; msToken=jCECxiDQ7zrlTUx9ISqhQIA2MgeqgD41TIW-EDuTU1zYavfXxUhCdEzkKSo8JHH8HW8twrAw2KAEMLPMbhB4YtE1yoPc5CJ8WmgLijMCishl2BkWvFwgYkz5gBwM5kUE3wf047IPbnSDzCk2EXa5_VPlaK7aKtv2EeF8Qmzktw==; perf_feed_cache={%22expireTimestamp%22:1791216000000%2C%22itemIds%22:[%227679111944200080658%22%2C%227685070548908412181%22%2C%227690608911828667670%22]}"""

# ================================================================
# INSTAGRAM — Akun dummy & Cookie Playwright
# ================================================================
IG_USERNAME = "scrapetsf_"
IG_PASSWORD = "Aghnasyarief3"
IG_COOKIE = "csrftoken=DcZZYVGNmquGu7LSwg0xKMkn9xFwdxkC; datr=Q880aqZUWs4FdxgCLTE5HpfM; dpr=1.25; ds_user_id=14889043079; ig_did=C6CF683D-04A5-45B4-A343-847BCB126C5F; ig_nrcb=1; mid=ajTPQwALAAG_xKDu3DzHJhAx6ox7; ps_l=1; ps_n=1; rur=PRN%2C17841414972371130%2C1791820760%3A01ff6e107617788e03a2e212e684571f27633f3da32e84fb98e44eaee9c172ab247e1186; sessionid=14889043079%3AaTerSZeSX4BVU2%3A25%3AAYmNbdBo3qyH3uQLWC16nFdgqDt_c_ZUdf2p7FLdow; wd=982x742"

# ================================================================
# FACEBOOK — Cookie dari browser
# ================================================================
FB_COOKIE = """locale=en_GB; dpr=1.25; c_user=61594469380108; xs=2:dwOR1nXMyApMJA:2:1790611279:-1:-1::AcwhG5CIuo5Mv_M3Es4jijJNllCV7QekzKfD6BgS2w; datr=kbk3arcnLLX4WpPK39N0LkG1; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1790611287010%2C%22v%22%3A1%7D; wd=982x742"""

# ================================================================
# TOPIK PENELITIAN: 2 TOPIK KEMENTERIAN PEKERJAAN UMUM
# Kuota:
# - Keyword Pertama per Topik : 10.000 data
# - Seluruh Keyword Sisanya   : 1.000 data
# ================================================================
TOPICS = {
    # 1. TOPIK 1: KEMENTERIAN PEKERJAAN UMUM (Fokus 5 Keyword Inti)
    "Kementerian_PU": [
        "Kementerian Pekerjaan Umum",
        "Kementerian PU",
        "Kementerian PU RI",
        "Kemen PU",
        "Kemen PU RI",
        "Kementerian Pekerjaan Umum Republik Indonesia",
        "KemenPU",
    ],

    # 2. TOPIK 2: MENTERI PU / MENTERI PEKERJAAN UMUM (Fokus 5 Keyword Inti)
    "Menteri_PU": [
        "Menteri Pekerjaan Umum",
        "Menteri PU",
        "Menteri PU Dody Hanggodo",
        "Menteri Dody Hanggodo",
        "Dody Hanggodo",
    ],
}

PRIMARY_TOPICS = {
    "Kementerian_PU": ["Kementerian Pekerjaan Umum"],
    "Menteri_PU": ["Menteri Pekerjaan Umum"],
}

# Hitung total keyword
total_keywords = sum(len(v) for v in TOPICS.values())
print("=" * 60)
print(f"[OK] KONFIGURASI SELESAI (PROJECT KEMEN PU RI)")
print(f"[INFO] Topik: {len(TOPICS)} topik (Kementerian_PU & Menteri_PU)")
print(f"[INFO] Keywords: {total_keywords} variasi keyword")
print(f"[INFO] Output: {OUTPUT_DIR}")
print("=" * 60)

for topic, keywords in TOPICS.items():
    print(f"\n[TOPIK] {topic}: {len(keywords)} keywords")
    for kw in keywords[:5]:
        print(f"   - {kw}")
    if len(keywords) > 5:
        print(f"   ... ({len(keywords) - 5} keyword lainnya)")

# ==============================================================================
# REGULASI FILTER TOPIK RESMI (STANDAR SORTING DATASET KEMEN PU)
# ==============================================================================

# 1. Pola Tokoh & Kepemimpinan (Menteri PU / Wamen / Dody Hanggodo)
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

# 2. Pola Institusi & Proyek (Kementerian PU / Ditjen / Infrastruktur)
pat_kemenpu_core = re.compile(
    r'\b(?:kemen[\s-]*pu(?:pr)?(?:\w*)|kement(?:eri|ri)an[\s-]+pekerjaan[\s-]+umum(?:\s+republik\s+indonesia|\s+ri)?|kemenpu(?:pr)?(?:\w*)|kement(?:eri|ri)an[\s-]+pu(?:pr)?(?:\s*ri)?|pu[\s-]+ri|pupr|kemenpupr)\b|'
    r'\b(?:departemen|dinas|sektor|instansi|lingkup|bidang|kantor)?[\s-]*pekerjaan[\s-]+umum\b|'
    r'#\w*(?:kemenpu|kemenpuri|kementerianpu|kementrianpu|kementerianpekerjaanumum|kementrianpekerjaanumum|pekerjaanumum|pupr|kemenpupr|bpsdmpu)\w*|'
    r'@\w*(?:kemenpu|kemenpu_|pupr|pekerjaanumum|binamarga|ciptakarya)\w*|'
    r'pu\.go\.id|'
    r'\b(?:politeknik[\s-]+pekerjaan[\s-]+umum|politeknik[\s-]+pu|k?dpupr|dinas[\s-]+pu(?:pr)?|kadis[\s-]*pu(?:pr)?\w*)\b|'
    r'\bditjen[\s-]+(?:bina[\s-]+marga|sumber[\s-]+daya[\s-]+air|cipta[\s-]+karya|bina[\s-]+konstruksi|pembiayaan[\s-]+infrastruktur)\b|'
    r'\bbina[\s-]+marga\b.{0,30}(?:pu|kementerian|kementrian|jalan|jembatan)|'
    r'\bcipta[\s-]+karya\b.{0,30}(?:pu|kementerian|kementrian|sanitasi|gedung)|'
    r'\bsumber[\s-]+daya[\s-]+air\b.{0,30}(?:pu|kementerian|kementrian|bendungan|irigasi)|'
    r'\b(?:bbws|bws|bbpjn|bpjn|bpsdm[\s-]+pu|bp2jk)\b',
    re.I
)

pat_kemenpu_cooccur = re.compile(
    r'(?:kementerian|kementrian|dinas|kantor|balai).{0,40}(?:pekerjaan\s+umum|\bpu\b|bina\s+marga|sda\b|cipta\s+karya)|'
    r'(?:pegawai|asn|pejabat|staf|inspektorat|lingkungan|internal|vendor|orang).{0,25}(?:kemen[\s-]*pu|\bpu\b|\bpupr\b|pekerjaan\s+umum)|'
    r'(?:pekerjaan\s+umum).{0,60}(?:republik\s+indonesia|ri\b|jalan\s+tol|jalan\s+nasional|jembatan|bendungan|irigasi|tanggul|banjir|infrastruktur|proyek|anggaran|tender|apbn|prabowo|tenaga)|'
    r'(?:infrastruktur|proyek|preservasi\s+jalan|normalisasi\s+sungai|penanganan\s+banjir).{0,50}(?:kemen\s*pu|pu\s*ri|kementerian\s*pu|kementrian\s*pu)',
    re.I
)

# 3. Filter Noise / False Positive
pat_noise_filter = re.compile(
    r'\b(?:pubg|pubgmobile|vario|lambretta|vespa|malaysia|darulnaimsquad|acah2pomen|puding|pupuk|puasa|purnama|puisi|pulau|pulang|putra|putri|pukul|punya|putus)\b',
    re.I
)

def detect_topic(content):
    """
    Mendeteksi apakah sebuah teks relevan dengan topik penelitian Kemen PU:
    Mengembalikan 'Menteri_PU', 'Kementerian_PU', atau None jika di luar topik.
    """
    if not content:
        return None
    c = str(content)

    is_menpu = bool(pat_menpu_core.search(c) or pat_menpu_cooccur.search(c))
    is_kemenpu = bool(pat_kemenpu_core.search(c) or pat_kemenpu_cooccur.search(c))

    if is_menpu and not is_kemenpu:
        return "Menteri_PU"
    if is_kemenpu and not is_menpu:
        return "Kementerian_PU"
    if is_menpu and is_kemenpu:
        # Jika kedua entitas muncul, prioritas ke Menteri_PU bila nama menteri/tokoh disebut eksplisit
        if pat_menpu_core.search(c):
            return "Menteri_PU"
        return "Kementerian_PU"

    # Noise check
    if pat_noise_filter.search(c):
        c_low = c.lower()
        if not any(k in c_low for k in ['pekerjaan umum', 'kemen pu', 'menteri pu', 'bina marga', 'dody hanggodo', 'infrastruktur']):
            return None

    return None

def is_relevant_topic(content):
    """Boolean check apakah teks relevan dengan topik penelitian Kemen PU."""
    return detect_topic(content) is not None
