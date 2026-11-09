# ============================================================
# KONFIGURASI KHUSUS TUGAS AKHIR (TA): ELEKTRIFIKASI KENDARAAN
# Objek Penelitian: Adopsi, Kebijakan, dan Ekosistem Kendaraan Listrik di Indonesia
# Model Analisis : IndoBERT Sentiment Analysis & Social Network Analysis (SNA)
# ============================================================

import os
import sys
import re

# Fix Windows console encoding
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
# KREDENSIAL API & COOKIES BROWSER
# ================================================================
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY_HERE"

TWITTER_COOKIES = {
    "auth_token": "687912004832a6234b5abcd93fad043ea267297d",
    "ct0": "1511710ab6133140b5e53033eb304ac563dda9643151557a41b65f4dee289a7b2fc9ec94e2da88946013d2bd7057caf05b49529a737d9075145d13b8c8b780473ffae48c74767babde6460cf7a8dc091",
}

TIKTOK_COOKIE = """delay_guest_mode_vid=5; g_state={"i_l":0,"i_ll":1782032495741,"i_b":"dBXb7unjIx9Yrqv6ZRXqzjduVh77FIgS/z1kLpU5RJU","i_e":{"enable_itp_optimization":24},"i_et":1782032495741}; last_login_method=google; _ttp=3Fkw4wHiesRWMah2CKvIPiWWeLH; passport_csrf_token=ad93fec592e3e1a3988700f04a58adfe; passport_csrf_token_default=ad93fec592e3e1a3988700f04a58adfe; myCookie=rap; s_v_web_id=verify_mudom0wp_e0oSJ2sB_XfHU_4S1S_9UoK_f6SGhQdpFwko; tiktok_webapp_theme_source=auto; tiktok_webapp_theme=dark; tt_ticket_guard_has_set_public_key=1; passport_fe_beating_status=true; waforiginalreid=https://www.tiktok.com/; waforigin_id=44; _waftokenid=eyJ2Ijp7ImEiOiIvRWswQ1JLdytYU092T3hEbnFOQktwQWhkdTFOMVRvSkFiYXVrVW5UVExZPSIsImIiOjE3OTA2MTE1MDUsImMiOiJYb3BrY3llWkU0RHM2aWVycm44dGdhNi96TG9iL245aG1mamJoc2orbENJPSJ9LCJzIjoiU0ZuZHVYM1pUeEJEUWlkVkY5eW5XU0F3ZjNOQVozYXlVNjZzekQxbCtGYz0ifQ; msToken=8Dwa7OAKeUeAG3S7OZxhHAvdTUqJWMt7A-rRWdcOTk5_5VrYulMwcV7WcQNIvUVHMiZPv5agmLIhRxXoFn_gB4Ru8jtRZqTvk8j9mWvNqeXBOIGIxs_3npUINIXRK-R26KvMwxyGmcIEfU4mGeUdGqMA7hrlAoo4dbcANmVrPzI=; msToken=jCECxiDQ7zrlTUx9ISqhQIA2MgeqgD41TIW-EDuTU1zYavfXxUhCdEzkKSo8JHH8HW8twrAw2KAEMLPMbhB4YtE1yoPc5CJ8WmgLijMCishl2BkWvFwgYkz5gBwM5kUE3wf047IPbnSDzCk2EXa5_VPlaK7aKtv2EeF8Qmzktw==; perf_feed_cache={%22expireTimestamp%22:1791216000000%2C%22itemIds%22:[%227679111944200080658%22%2C%227685070548908412181%22%2C%227690608911828667670%22]}"""

IG_USERNAME = "scrapetsf_"
IG_PASSWORD = "Aghnasyarief3"
IG_COOKIE = "csrftoken=DcZZYVGNmquGu7LSwg0xKMkn9xFwdxkC; datr=Q880aqZUWs4FdxgCLTE5HpfM; dpr=1.25; ds_user_id=14889043079; ig_did=C6CF683D-04A5-45B4-A343-847BCB126C5F; ig_nrcb=1; mid=ajTPQwALAAG_xKDu3DzHJhAx6ox7; ps_l=1; ps_n=1; rur=PRN%2C17841414972371130%2C1791820760%3A01ff6e107617788e03a2e212e684571f27633f3da32e84fb98e44eaee9c172ab247e1186; sessionid=14889043079%3AaTerSZeSX4BVU2%3A25%3AAYmNbdBo3qyH3uQLWC16nFdgqDt_c_ZUdf2p7FLdow; wd=982x742"

FB_COOKIE = """locale=en_GB; dpr=1.25; c_user=61594469380108; xs=2:dwOR1nXMyApMJA:2:1790611279:-1:-1::AcwhG5CIuo5Mv_M3Es4jijJNllCV7QekzKfD6BgS2w; datr=kbk3arcnLLX4WpPK39N0LkG1; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1790611287010%2C%22v%22%3A1%7D; wd=982x742"""

# ================================================================
# DIREKTORI OUTPUT KHUSUS SKRIPSI / TA
# Memastikan 100% terpisah dari data project lain
# ================================================================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ScrapeData_TA_Elektrifikasi')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================================================
# TOPIK PENELITIAN TA: ELEKTRIFIKASI KENDARAAN (FOKUS PLUS-MINUS & SENTIMEN MURNI)
# Tanpa nama brand (merek), tanpa kata harga/angka relatif.
# Fokus kuat pada kelebihan (plus), kekurangan (minus), keluhan, kepuasan,
# dan evaluasi nyata publik untuk training IndoBERT & analisis polaritas SNA.
# Regulasi Kuota:
# - Keyword Pertama per Topik : Target 10.000 data
# - Seluruh Keyword Sisanya   : Target 1.000 data
# ================================================================
TOPICS = {
    # 1. OBJEK UTAMA: ELEKTRIFIKASI KENDARAAN (Ekosistem, Transisi, Fasilitas SPKLU, Isu Lingkungan & Baterai)
    "Elektrifikasi_Kendaraan": [
        "elektrifikasi kendaraan",             # [UTAMA: Target 10.000 data]
        "kendaraan listrik",                   # Netral / Umum
        "kelebihan kendaraan listrik",         # Plus / Keunggulan
        "manfaat elektrifikasi kendaraan",     # Plus / Manfaat
        "kendaraan listrik ramah lingkungan",  # Plus / Lingkungan
        "kemudahan SPKLU",                     # Plus / Fasilitas
        "kekurangan kendaraan listrik",        # Minus / Kelemahan
        "bahaya kendaraan listrik",            # Minus / Risiko
        "masalah SPKLU",                       # Minus / Kendala Fasilitas
        "keluhan SPKLU",                       # Minus / Keluhan Konsumen
        "limbah baterai kendaraan listrik",    # Minus / Masalah Lingkungan
        "pro kontra kendaraan listrik",        # Evaluatif / Debat Publik
        "polemik kendaraan listrik",           # Evaluatif / Polemik
        "keamanan kendaraan listrik",          # Evaluatif / Keselamatan
        "evaluasi elektrifikasi kendaraan"     # Evaluatif / Kebijakan
    ],

    # 2. OBJEK UTAMA: MOBIL LISTRIK (Opini Roda 4, Plus-Minus, Baterai, Pengalaman Pakai)
    "Mobil_Listrik": [
        "mobil listrik",                       # [UTAMA: Target 10.000 data]
        "kelebihan mobil listrik",             # Plus / Keunggulan
        "keuntungan mobil listrik",            # Plus / Keuntungan
        "puas pakai mobil listrik",            # Plus / Kepuasan Nyata
        "kelebihan baterai mobil listrik",     # Plus / Performa Baterai
        "kenyamanan mobil listrik",            # Plus / Fitur & Kenyamanan
        "kekurangan mobil listrik",            # Minus / Kelemahan
        "kekurangan baterai mobil listrik",    # Minus / Isu Baterai
        "keluhan mobil listrik",               # Minus / Keluhan Konsumen
        "masalah mobil listrik",               # Minus / Problem
        "kecewa beli mobil listrik",           # Minus / Kekecewaan
        "kebakaran mobil listrik",             # Minus / Isu Keselamatan
        "kelemahan mobil listrik",             # Minus / Keterbatasan
        "kontroversi mobil listrik",           # Evaluatif / Pro-Kontra
        "pengalaman pakai mobil listrik"       # Evaluatif / Review Nyata
    ],

    # 3. OBJEK UTAMA: MOTOR LISTRIK (Opini Roda 2, Plus-Minus, Konversi, Swap Baterai)
    "Motor_Listrik": [
        "motor listrik",                       # [UTAMA: Target 10.000 data]
        "kelebihan motor listrik",             # Plus / Keunggulan
        "keuntungan motor listrik",            # Plus / Keuntungan
        "puas pakai motor listrik",            # Plus / Kepuasan Nyata
        "kelebihan baterai motor listrik",     # Plus / Performa Baterai
        "kemudahan swap baterai motor listrik",# Plus / Swap Baterai
        "kekurangan motor listrik",            # Minus / Kelemahan
        "kekurangan baterai motor listrik",    # Minus / Isu Baterai
        "keluhan motor listrik",               # Minus / Keluhan Pengguna
        "masalah motor listrik",               # Minus / Problem
        "kecewa motor listrik",                # Minus / Kekecewaan
        "kendala konversi motor listrik",      # Minus / Hambatan Konversi
        "kelemahan motor listrik",             # Minus / Keterbatasan
        "kontroversi motor listrik",           # Evaluatif / Pro-Kontra
        "pengalaman pakai motor listrik"       # Evaluatif / Review Nyata
    ]
}

PRIMARY_TOPICS = {
    "Elektrifikasi_Kendaraan": ["elektrifikasi kendaraan"],
    "Mobil_Listrik": ["mobil listrik"],
    "Motor_Listrik": ["motor listrik"],
}

# ==============================================================================
# [ARSIP / CADANGAN] TOPICS VERSI 23 KEYWORDS (DIKOMENTARI, JANGAN DIHAPUS)
# ==============================================================================
# TOPICS_V2_23KWS = {
#     "Elektrifikasi_Kendaraan": [
#         "elektrifikasi kendaraan",
#         "kendaraan listrik",
#         "polemik kendaraan listrik",
#         "pro kontra kendaraan listrik",
#         "kendaraan listrik ramah lingkungan",
#         "masalah SPKLU",
#         "keluhan SPKLU",
#         "keamanan kendaraan listrik",
#         "bahaya kendaraan listrik"
#     ],
#     "Mobil_Listrik": [
#         "mobil listrik",
#         "keluhan mobil listrik",
#         "kecewa beli mobil listrik",
#         "puas pakai mobil listrik",
#         "kontroversi mobil listrik",
#         "masalah mobil listrik",
#         "kebakaran mobil listrik"
#     ],
#     "Motor_Listrik": [
#         "motor listrik",
#         "keluhan motor listrik",
#         "kecewa motor listrik",
#         "puas pakai motor listrik",
#         "kontroversi motor listrik",
#         "masalah motor listrik",
#         "kendala konversi motor listrik"
#     ]
# }

# ==============================================================================
# [ARSIP / CADANGAN] TOPICS V1 (DIKOMENTARI, JANGAN DIHAPUS)
# ==============================================================================
# TOPICS_V1_BACKUP = {
#     "Elektrifikasi_Kendaraan": [
#         "elektrifikasi kendaraan",
#         "kendaraan listrik",
#         "polemik kendaraan listrik",
#         "kendaraan listrik ramah lingkungan",
#         "efektivitas subsidi kendaraan listrik",
#         "masalah SPKLU",
#         "keamanan baterai kendaraan listrik",
#     ],
#     "Mobil_Listrik": [
#         "mobil listrik",
#         "kontroversi mobil listrik",
#         "keluhan mobil listrik",
#         "masalah mobil listrik",
#         "kelebihan dan kelemahan mobil listrik",
#         "pengalaman pakai mobil listrik",
#         "kebakaran mobil listrik",
#     ],
#     "Motor_Listrik": [
#         "motor listrik",
#         "kontroversi motor listrik",
#         "keluhan motor listrik",
#         "masalah motor listrik",
#         "subsidi motor listrik sepi",
#         "kendala konversi motor listrik",
#         "pengalaman motor listrik",
#     ]
# }

# ==============================================================================
# [ARSIP / CADANGAN] TOPICS DETAIL DENGAN 105 KEYWORDS (DIKOMENTARI, JANGAN DIHAPUS)
# ==============================================================================
# TOPICS_DETAIL_BACKUP = {
#     "Mobil_Listrik": [
#         "mobil listrik",
#         "kendaraan listrik",
#         "electric vehicle indonesia",
#         "mobil listrik indonesia",
#         "insentif mobil listrik",
#         "subsidi mobil listrik",
#         "pajak mobil listrik",
#         "PPN DTP mobil listrik",
#         "harga mobil listrik",
#         "mobil listrik murah",
#         "Wuling Air EV",
#         "Wuling Binguo",
#         "Hyundai Ioniq",
#         "Hyundai Kona Electric",
#         "BYD Indonesia",
#         "mobil listrik BYD",
#         "Chery Omoda E5",
#         "mobil listrik cina",
#         "mobil listrik mogok",
#         "kebakaran mobil listrik",
#         "baterai mobil listrik rusak",
#         "kelemahan mobil listrik",
#         "kelebihan mobil listrik",
#         "mobil listrik banjir",
#         "mobil listrik vs bensin",
#         "mobil listrik gagal",
#         "mobil listrik berhasil",
#         "mobil listrik kontroversi",
#         "mobil listrik kritik",
#         "mobil listrik emisi",
#         "mobil listrik prabowo",
#         "mobil listrik garuda",
#         "mobil listrik maung",
#         "mobil listrik mewah",
#         "mobil listrik lcgc"
#     ],
#     "Motor_Listrik": [
#         "motor listrik",
#         "subsidi motor listrik",
#         "motor listrik subsidi",
#         "subsidi 7 juta motor listrik",
#         "motor listrik 7 juta",
#         "konversi motor listrik",
#         "bengkel konversi motor listrik",
#         "motor listrik indonesia",
#         "Gesits motor listrik",
#         "Polytron Fox R",
#         "motor listrik Alva",
#         "Alva Cervo",
#         "motor listrik Volta",
#         "motor listrik United",
#         "Honda EM1 e",
#         "motor listrik Honda",
#         "motor listrik Yamaha",
#         "motor listrik murah",
#         "motor listrik rusak",
#         "kelemahan motor listrik",
#         "kelebihan motor listrik",
#         "baterai motor listrik",
#         "motor listrik sepi peminat",
#         "subsidi motor listrik sepi",
#         "motor listrik mogok",
#         "motor listrik banjir",
#         "motor listrik vs bensin",
#         "motor listrik gagal",
#         "motor listrik berhasil",
#         "motor listrik kontroversi",
#         "motor listrik kritik",
#         "tarikan motor listrik",
#         "motor listrik ojol",
#         "ojek online motor listrik",
#         "jarak tempuh motor listrik"
#     ],
#     "Infrastruktur_Baterai": [
#         "SPKLU",
#         "baterai kendaraan listrik",
#         "SPKLU PLN",
#         "stasiun pengisian kendaraan listrik",
#         "ngecas mobil listrik",
#         "charging station mobil listrik",
#         "SPBKLU",
#         "swap baterai motor listrik",
#         "pabrik baterai mobil listrik",
#         "hilirisasi nikel baterai",
#         "baterai nikel vs LFP",
#         "limbah baterai mobil listrik",
#         "daur ulang baterai EV",
#         "tarif listrik SPKLU",
#         "antrean SPKLU",
#         "SPKLU rusak",
#         "SPKLU rest area",
#         "SPKLU mudik",
#         "kebijakan elektrifikasi kendaraan",
#         "transisi energi kendaraan listrik",
#         "kendaraan listrik emisi karbon",
#         "kendaraan listrik ramah lingkungan",
#         "kendaraan listrik PLTU batubara",
#         "kebakaran baterai listrik",
#         "SPKLU gagal",
#         "SPKLU berhasil",
#         "SPKLU kontroversi",
#         "SPKLU kritik",
#         "baterai motor listrik mahal",
#         "kapasitas baterai EV",
#         "waktu pengecasan SPKLU",
#         "fast charging SPKLU",
#         "PLN kendaraan listrik",
#         "ekosistem kendaraan listrik",
#         "subsidi konversi baterai"
#     ]
# }

# ================================================================
# REGEX MATCHER UNTUK IN-FLIGHT TOPIC REGULATION (TA ELEKTRIFIKASI)
# ================================================================

pat_mobil_core = re.compile(
    r'\b(?:mobil\s*listrik|wuling\s*(?:air\s*ev|binguo|cloud)|hyundai\s*(?:ioniq|kona)|byd(?:\s*indonesia)?|omoda\s*e5|chery\s*(?:omoda|e5)|insentif\s*mobil\s*listrik|ppn\s*dtp\s*(?:mobil|ev)|ev\s*car|electric\s*car|mobil\s*ev|molis|mobil\s*ramah\s*lingkungan)\b|'
    r'#?\w*mobillistrik\w*|#?\w*electrivehicle\w*|#?\w*wulingairev\w*|#?\w*hyundaiioniq\w*',
    re.I
)

pat_motor_core = re.compile(
    r'\b(?:motor\s*listrik|molis\b|gesits|polytron\s*fox|alva\s*(?:cervo|one)|volta|united\s*(?:e-motor|t1800)|honda\s*em1|yamaha\s*(?:e-vino|e01)|konversi\s*motor\s*(?:listrik|bensin)|subsidi\s*motor\s*listrik|motor\s*ev|electric\s*motorcycle)\b|'
    r'#?\w*motorlistrik\w*|#?\w*konversimotorlistrik\w*|#?\w*subsidimotorlistrik\w*',
    re.I
)

pat_infra_core = re.compile(
    r'\b(?:spklu|spbklu|charging\s*station|stasiun\s*pengisian\s*kendaraan\s*listrik|swap\s*baterai|baterai\s*(?:ev|kendaraan\s*listrik|lithium|lfp|nikel)|hilirisasi\s*nikel|pabrik\s*baterai|limbah\s*baterai|daur\s*ulang\s*baterai|ngecas\s*(?:mobil|motor)\s*listrik|fast\s*charging\s*ev|pengecasan\s*kendaraan\s*listrik)\b|'
    r'#?\w*spklu\w*|#?\w*spbklu\w*|#?\w*bateraiev\w*|#?\w*baterailistrik\w*',
    re.I
)

pat_general_ev = re.compile(
    r'\b(?:kendaraan\s*listrik|elektrifikasi\s*(?:kendaraan|transportasi)|electric\s*vehicle|kendaraan\s*berbasis\s*baterai|klbb|kblbb)\b|'
    r'#?\w*kendaraanlistrik\w*|#?\w*electricvehicle\w*|#?\w*kblbb\w*',
    re.I
)

def detect_topic(content):
    """
    In-flight Topic Detection untuk Tugas Akhir (Elektrifikasi Kendaraan).
    Mengembalikan 'Elektrifikasi_Kendaraan', 'Mobil_Listrik', 'Motor_Listrik',
    atau None jika di luar konteks elektrifikasi kendaraan.
    """
    if not content:
        return None
    c = str(content)
    
    is_motor = bool(pat_motor_core.search(c))
    is_mobil = bool(pat_mobil_core.search(c))
    
    # 1. Jika membahas kedua-duanya sekaligus (mobil & motor listrik), masukkan ke payung Elektrifikasi_Kendaraan
    if is_motor and is_mobil:
        return "Elektrifikasi_Kendaraan"
    # 2. Cek kecocokan motor listrik spesifik
    if is_motor:
        return "Motor_Listrik"
    # 3. Cek kecocokan mobil listrik spesifik
    if is_mobil:
        return "Mobil_Listrik"
    # 4. Cek infrastruktur (SPKLU, baterai) & elektrifikasi kendaraan umum
    if pat_infra_core.search(c) or pat_general_ev.search(c):
        return "Elektrifikasi_Kendaraan"
        
    return None

def is_relevant_topic(content):
    """Boolean check apakah konten relevan dengan Elektrifikasi Kendaraan."""
    return detect_topic(content) is not None
