"""
Tab Analisis Sentimen Terpadu & Deteksi Wilayah Terdampak
===========================================================
Mengintegrasikan 5 Pilar Analisis per Sentimen:
1. Isu Dominan (Top Klaster Isu)
2. Daerah Terdampak (Deteksi Wilayah/Provinsi/Balai PU)
3. Platform Media & Sosial (Distribusi Kanal dengan Logo Platform)
4. Akun Pemengaruh (Top Influencers / Penyebar Utama)
5. Postingan Nyata (Daftar Kartu Postingan dengan Filter & Tautan Asli)
"""

import re
import html
import streamlit as st
import pandas as pd
import plotly.express as px
from src.clean_header_footer import render_html
from src.mh_style import render_logo_badge
from src.icons import get_platform_icon, get_ui_icon, PLATFORM_COLORS

# Gazetteer Wilayah & Locus Proyek / Balai PU
REGION_GAZETTEER = [
    ("Sumatera", r"\b(?:sumatera|sumut|sumbar|sumsel|medan|padang|aceh|riau|pekanbaru|palembang|lampung|jambi|bengkulu|geurutee|danau\s+toba|toba|samosir|deli\s+serdang|langkat|asahan|batang\s+toru|bws\s+sumatera|bpjn\s+aceh|bpjn\s+sumut|bpjn\s+sumbar|bpjn\s+riau|bbpjn\s+sumatera)\b"),
    ("DKI Jakarta & Sekitarnya", r"\b(?:jakarta|jaksel|jaktim|jakbar|jakpus|jakut|pattimura|monas|ciliwung|cisadane|kebon\s+pala|kampung\s+melayu|kp\s+melayu|mrt\s+jakarta|lrt\s+jakarta|transjakarta|bbws\s+ciliwung|bbpjn\s+dki)\b"),
    ("Jawa Barat & Banten", r"(?<!pantai\s)\b(?:jabar|jawa\s+barat|bandung|bogor|depok|bekasi|banten|tangerang|tangsel|cirebon|sukabumi|citarum|cisadane|serang|lebak|pandeglang|karawang|purwakarta|subang|majalengka|kuningan|bbws\s+citarum|bbpjn\s+dki-jabar|bpjn\s+banten)\b"),
    ("Jawa Tengah & Pantura", r"\b(?:jateng|jawa\s+tengah|semarang|demak|kudus|solo|surakarta|pantura|pemali\s+juana|bengawan\s+solo|pekalongan|brebes|banyumas|purwokerto|cilacap|kebumen|magelang|klaten|sukoharjo|wonogiri|karanganyar|sragen|grobogan|pati|rembang|blora|temanggung|kendal|batang|bbws\s+bengawan\s+solo|bbws\s+pemali\s+juana|bbpjn\s+jateng)\b"),
    ("D.I. Yogyakarta", r"\b(?:jogja|yogyakarta|wisatajogja|diy|kulon\s+progo|sleman|bantul|parangtritis|pantai\s+depok|gunungkidul|jjls|progo|opak|merapi|bbws\s+serayu\s+opak|bbpjn\s+jateng-diy)\b"),
    ("Jawa Timur", r"\b(?:jatim|jawa\s+timur|surabaya|malang|batu|brantas|sidoarjo|banyuwangi|kediri|madura|gresik|mojokerto|jombang|blitar|madiun|tuban|lamongan|bojonegoro|ngawi|magetan|ponorogo|pacitan|trenggalek|tulungagung|lumajang|jember|bondowoso|situbondo|probolinggo|pasuruan|bbws\s+brantas|bbpjn\s+jatim)\b"),
    ("Kalimantan & IKN", r"\b(?:kalimantan|ikn|nusantara|kaltim|kalsel|kalbar|kalteng|kaltara|balikpapan|samarinda|pontianak|banjarmasin|palangkaraya|tarakan|penajam|paser|sepaku|bws\s+kalimantan|bpjn\s+kaltim|bpjn\s+kalbar|bpjn\s+kalsel)\b"),
    ("Sulawesi", r"\b(?:sulawesi|sulsel|sulut|sulteng|sultra|makassar|manado|palu|kendari|wajo|bitung|mamuju|sulbar|gorontalo|gowa|maros|bone|parepare|palopo|bws\s+sulawesi|bbpjn\s+sulsel|bpjn\s+sulut)\b"),
    ("Bali & Nusa Tenggara", r"\b(?:bali|denpasar|badung|gianyar|tabanan|buleleng|jembrana|karangasem|klungkung|bangli|lombok|ntb|ntt|kupang|flores|mataram|sumbawa|labuan\s+bajo|bws\s+bali|bpjn\s+bali|bpjn\s+ntb|bpjn\s+ntt)\b"),
    ("Maluku & Papua", r"\b(?:maluku|papua|ambon|ternate|tidore|jayapura|merauke|sorong|manokwari|mimika|timika|biak|seram|bws\s+maluku|bws\s+papua|bpjn\s+jayapura|bpjn\s+merauke|bpjn\s+sorong)\b"),
]

# Definisi Klaster Isu Utama
ISSUE_PATTERNS = [
    ("Preservasi & Kerusakan Jalan", r"\b(?:jalan[\s-]+rusak|jalan[\s-]+berlubang|jalan[\s-]+bolong|aspal|preservasi[\s-]+jalan|sapu[\s-]+lubang|jalur[\s-]+pantura|jalan[\s-]+daerah|inpres[\s-]+jalan|ijd)\b"),
    ("Bendungan, Tanggul & Bencana Banjir", r"\b(?:bendungan|tanggul|banjir|rob|normalisasi[\s-]+sungai|irigasi|air[\s-]+baku|bbws|pintu[\s-]+air|drainase|bencana|longsor)\b"),
    ("Jembatan & Konektivitas Wilayah", r"\b(?:jembatan|flyover|underpass|konektivitas|akses[\s-]+jalan|jembatan[\s-]+gantung)\b"),
    ("Tata Kelola, Tender & Anggaran APBN", r"\b(?:anggaran|apbn|tender|lelang|vendor|kontraktor|itjen|inspektorat|efisiensi|pagu|korupsi|kpk)\b"),
    ("Fasilitas Publik, Sanitasi & Gedung", r"\b(?:sekolah[\s-]+rakyat|perpustakaan|perpus|sanitasi|air[\s-]+minum|spam|cipta[\s-]+karya|gedung|wfc|taman|pasar)\b"),
    ("Kebijakan & Kepemimpinan Menteri PU", r"\b(?:menteri[\s-]+pu|dody[\s-]+hanggodo|wamen|kunker|sidak|arahan|rakor|kebijakan|kabinet)\b"),
]

_INVISIBLE_CHARS_RE = re.compile(r'[\s\u200b-\u200f\u202a-\u202e\u2060\u3164\u2800\ufeff\u115f\u1160\uffa0\xa0]+')
_SOCIAL_PLATFORMS = {'Twitter', 'Instagram', 'Threads', 'TikTok'}
_URL_HANDLE_PATTERNS = [
    re.compile(r'tiktok\.com/@([^/?#]+)', re.IGNORECASE),
    re.compile(r'threads\.(?:net|com)/@([^/?#]+)', re.IGNORECASE),
    re.compile(r'youtube\.com/@([^/?#]+)', re.IGNORECASE),
    re.compile(r'instagram\.com/([^/?#]+)', re.IGNORECASE),
    re.compile(r'(?:twitter|x)\.com/([^/?#]+)', re.IGNORECASE),
]
_INVALID_URL_SEGMENTS = {'p', 'reel', 'reels', 'watch', 'photo', 'groups', 'share', 'explore', 'search', 'hashtag', 'i'}


def extract_affected_region(text):
    if not text or pd.isna(text):
        return "Nasional / Terpusat"
    t = str(text).lower()
    best_region = None
    best_hits = 0
    for reg, pat in REGION_GAZETTEER:
        hits = len(re.findall(pat, t))
        if hits > best_hits:
            best_hits = hits
            best_region = reg
    return best_region if best_region else "Nasional / Terpusat"


def extract_issue_category(text):
    if not text or pd.isna(text):
        return "Isu Umum Infrastruktur"
    t = str(text).lower()
    for name, pat in ISSUE_PATTERNS:
        if re.search(pat, t):
            return name
    return "Isu Umum Infrastruktur"


def get_issue_solution(issue_name):
    """Mengembalikan solusi kebijakan taktis dan unit penanggung jawab di Kementerian PU."""
    solutions_map = {
        "Preservasi & Kerusakan Jalan": {
            "unit": "Ditjen Bina Marga / BBPJN & BPJN Wilayah",
            "sla": "24 - 48 Jam",
            "tindakan": "Mobilisasi Tim Reaksi Cepat 'Sapu Lubang' untuk penambalan darurat ruas jalan nasional & jalur logistik; unggah dokumentasi visual 'Before-After' di medsos untuk memotong kaskade kemarahan publik.",
            "target": "Jalur Pantura, Lintas Sumatera, dan konektivitas lingkar kota utama."
        },
        "Bendungan, Tanggul & Bencana Banjir": {
            "unit": "Ditjen Sumber Daya Air / BBWS & BWS Wilayah",
            "sla": "12 - 24 Jam (Siaga 1)",
            "tindakan": "Aktivasi posko siaga banjir 24 jam; mobilisasi alat berat, geobag, dan bronjong darurat pada tanggul kritis; publikasi berkala elevasi Tinggi Muka Air (TMA) dan kesiapan pompa mobile.",
            "target": "BBWS Ciliwung-Cisadane, BBWS Citarum, BBWS Bengawan Solo, BBWS Brantas."
        },
        "Jembatan & Konektivitas Wilayah": {
            "unit": "Balai Jembatan Khusus & Terowongan / Ditjen Bina Marga",
            "sla": "1 - 3 Hari",
            "tindakan": "Inspeksi struktural berkala beban dinamis; penegakan pembatasan tonase muatan lebih (ODOL); penyiapan jembatan rangka baja bailey portabel pada ruas terdampak putus.",
            "target": "Ruas penghubung antar-kabupaten/provinsi dan jembatan gantung perintis."
        },
        "Tata Kelola, Tender & Anggaran APBN": {
            "unit": "Inspektorat Jenderal (Itjen) & Biro Komunikasi Publik",
            "sla": "1 x 24 Jam",
            "tindakan": "Pernyataan resmi satu pintu (single-voice response); klarifikasi integritas proses e-katalog/LPSE; transparansi tindak lanjut rekomendasi audit BPK/KPK.",
            "target": "Paket tender strategis nasional dan pengawasan akuntabilitas vendor."
        },
        "Fasilitas Publik, Sanitasi & Gedung": {
            "unit": "Ditjen Cipta Karya & Pengelola Fasilitas KemenPU",
            "sla": "24 Jam",
            "tindakan": "Peningkatan standar operasional sarana publik (AC, wifi, kebersihan, jam buka perpus/ruang baca); percepatan jaringan perpipaan SPAM dan sanitasi pemukiman.",
            "target": "Perpustakaan KemenPU Pattimura, Gedung Cipta Karya, fasilitas SPAM daerah."
        },
        "Kebijakan & Kepemimpinan Menteri PU": {
            "unit": "Staf Khusus Menteri & Biro Komunikasi Publik",
            "sla": "Seketika (Real-time)",
            "tindakan": "Diseminasi video kerja nyata Menteri PU (kunker, sidak lapangan tanpa protokoler kaku, respon cepat arahan Presiden); kolaborasi publikasi dengan Komisi V DPR RI.",
            "target": "Kanal media sosial resmi @kemenpu, portal berita nasional, dan platform X/TikTok."
        }
    }
    return solutions_map.get(issue_name, {
        "unit": "Unit Kerja Terkait Kementerian PU",
        "sla": "24 - 48 Jam",
        "tindakan": "Evaluasi teknis lapangan, verifikasi aduan masyarakat melalui kanal LAPOR/medsos, dan koordinasi cepat dengan Balai setempat.",
        "target": "Seluruh wilayah kerja Kementerian PU."
    })


def fmt_val(num):
    try:
        val = float(num)
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val/1_000:.1f}K"
        return f"{int(val):,}"
    except Exception:
        return "0"


def _has_visible_alnum(text):
    cleaned = _INVISIBLE_CHARS_RE.sub(' ', str(text or '')).strip()
    return bool(re.search(r'[A-Za-z0-9]', cleaned))


def _resolve_author_info(author, handle='', url='', platform=''):
    """Resolves clean display name and avatar initials, falling back from blank/invisible nicknames."""
    cand = _INVISIBLE_CHARS_RE.sub(' ', str(author or '')).strip()
    h_cand = _INVISIBLE_CHARS_RE.sub(' ', str(handle or '')).strip()

    chosen = ""
    if _has_visible_alnum(cand) and cand.lower() not in ('nan', 'none', 'null', 'unknown', 'anonim'):
        chosen = cand
    elif _has_visible_alnum(h_cand) and h_cand.lower() not in ('nan', 'none', 'null', 'unknown', 'anonim'):
        chosen = h_cand
    else:
        url_str = str(url or '').strip()
        for pat in _URL_HANDLE_PATTERNS:
            m = pat.search(url_str)
            if m:
                seg = m.group(1).strip()
                if seg.lower() not in _INVALID_URL_SEGMENTS and _has_visible_alnum(seg):
                    chosen = f"@{seg.lstrip('@')}"
                    break

    if not chosen:
        chosen = "Anonim"

    plat_str = str(platform or '').strip()
    if plat_str in _SOCIAL_PLATFORMS and chosen != "Anonim":
        # Prefix @ only when handle-like (no spaces) or already starts with @
        if chosen.startswith('@'):
            chosen = f"@{chosen.lstrip('@')}"
        elif ' ' not in chosen:
            chosen = f"@{chosen}"

    return chosen


def _get_initials(display_name):
    raw = str(display_name or '').strip().lstrip('@')
    tokens = re.findall(r'[A-Za-z0-9]+', raw)
    if not tokens:
        return "AN"
    if ' ' in raw and len(tokens) >= 2:
        return (tokens[0][0] + tokens[1][0]).upper()
    if len(tokens[0]) >= 2:
        return tokens[0][:2].upper()
    if len(tokens) >= 2:
        return (tokens[0][0] + tokens[1][0]).upper()
    return tokens[0][0].upper()


def _section_header_html(number, title, icon_name, accent_color="#0F2942", right_badge=""):
    icon_svg = get_ui_icon(icon_name, size=15, color=accent_color)
    badge_html = (
        f'<span style="font-size:10px; font-weight:700; color:#475569; background:#F1F5F9; '
        f'padding:2px 8px; border-radius:999px; border:1px solid #E2E8F0; white-space:nowrap;">{html.escape(right_badge)}</span>'
        if right_badge else ""
    )
    return (
        f'<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; '
        f'padding-bottom:9px; margin-bottom:10px; border-bottom:1px solid #F1F5F9;">'
        f'<div style="display:flex; align-items:center; gap:8px; min-width:0;">'
        f'<span style="width:28px; height:28px; border-radius:7px; background:{accent_color}14; '
        f'border:1px solid {accent_color}30; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;">{icon_svg}</span>'
        f'<span style="font-size:14px; font-weight:800; color:#0F2942; line-height:1.25;">{number}. {html.escape(title)}</span>'
        f'</div>'
        f'{badge_html}'
        f'</div>'
    )


def _inject_sentiment_button_styles(selected_sent):
    """Scoped CSS styling for the 3 sentiment filter buttons with semantic borders/tints."""
    def _rule(key, border, bg, txt, is_active):
        if is_active:
            return (
                f'.st-key-{key} button {{ background:{bg} !important; border:2px solid {border} !important; '
                f'color:{txt} !important; box-shadow:0 2px 8px {border}24 !important; border-radius:10px !important; '
                f'min-height:58px !important; transition:all 0.15s ease !important; }}'
                f'.st-key-{key} button p, .st-key-{key} button span, .st-key-{key} button svg {{ color:{txt} !important; font-weight:800 !important; }}'
            )
        return (
            f'.st-key-{key} button {{ background:#FFFFFF !important; border:1px solid #E2E8F0 !important; '
            f'color:#334155 !important; border-radius:10px !important; min-height:58px !important; transition:all 0.15s ease !important; }}'
            f'.st-key-{key} button:hover {{ background:{bg} !important; border-color:{border} !important; color:{txt} !important; }}'
        )

    css = (
        "<style>"
        + _rule("btn_sent_neg", "#EF4444", "#FEF2F2", "#B91C1C", selected_sent == "Negatif")
        + _rule("btn_sent_net", "#64748B", "#F1F5F9", "#334155", selected_sent == "Netral")
        + _rule("btn_sent_pos", "#10B981", "#ECFDF5", "#047857", selected_sent == "Positif")
        + "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)


def render_tab_sentiment_drilldown(df_filtered, **kwargs):
    """
    Menampilkan tab eksplorasi sentimen multi-dimensi secara interaktif tanpa emoji.
    """
    if df_filtered.empty:
        st.warning("Tidak ada data yang tersedia untuk filter saat ini.")
        return

    df = df_filtered.copy()

    # Pastikan kolom wilayah & kategori isu tersedia
    text_col = 'cleaned_content' if 'cleaned_content' in df.columns else ('raw_content' if 'raw_content' in df.columns else None)
    if 'detected_region' not in df.columns:
        df['detected_region'] = df[text_col].apply(extract_affected_region) if text_col else "Nasional / Terpusat"
    if 'issue_category' not in df.columns:
        df['issue_category'] = df[text_col].apply(extract_issue_category) if text_col else "Isu Umum Infrastruktur"

    tot_all = len(df)
    sent_series = df['sentiment_name'].astype(str) if 'sentiment_name' in df.columns else pd.Series('Netral', index=df.index)
    n_neg = int((sent_series == 'Negatif').sum())
    n_net = int((sent_series == 'Netral').sum())
    n_pos = int((sent_series == 'Positif').sum())

    pct_neg = (n_neg / tot_all * 100) if tot_all > 0 else 0.0
    pct_net = (n_net / tot_all * 100) if tot_all > 0 else 0.0
    pct_pos = (n_pos / tot_all * 100) if tot_all > 0 else 0.0

    # Header Utama dengan Logo Platform
    logo_html = render_logo_badge(size=38)
    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:16px 20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(15,23,42,0.04); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
        <div style="display:flex; align-items:center; gap:14px; min-width:0; flex:1;">
            {logo_html}
            <div style="min-width:0;">
                <span style="display:inline-block; background:#0F2942; color:#FFFFFF; font-size:10px; font-weight:800; padding:3px 9px; border-radius:4px; letter-spacing:0.6px; margin-bottom:5px;">EKSPLORASI SENTIMEN MULTIDIMENSI</span>
                <div style="color:#0F2942; font-size:18px; font-weight:800; line-height:1.25;">Analisis Isu, Post, Akun, Platform &amp; Wilayah Terdampak</div>
                <div style="font-size:12px; color:#64748B; margin-top:3px; line-height:1.4;">Pilih kategori sentimen untuk membedah isu dominan, wilayah terdampak, kanal media, top pemengaruh, dan postingan aslinya.</div>
            </div>
        </div>
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:8px 14px; text-align:right; flex-shrink:0;">
            <div style="font-size:10px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL KORPUS AKTIF</div>
            <div style="font-size:20px; font-weight:800; color:#0F2942; line-height:1.2;">{tot_all:,} <span style="font-size:11px; font-weight:600; color:#64748B;">post</span></div>
        </div>
    </div>
    """)

    # State switcher sentimen
    if 'active_drilldown_sent' not in st.session_state:
        st.session_state['active_drilldown_sent'] = 'Negatif'

    def _set_active_sent(val):
        st.session_state['active_drilldown_sent'] = val

    _inject_sentiment_button_styles(st.session_state['active_drilldown_sent'])

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        st.button(
            f"SENTIMEN NEGATIF  \n{n_neg:,} post ({pct_neg:.1f}%)",
            icon=":material/error_outline:",
            use_container_width=True,
            key="btn_sent_neg",
            on_click=_set_active_sent,
            args=("Negatif",),
        )
    with col_btn2:
        st.button(
            f"SENTIMEN NETRAL  \n{n_net:,} post ({pct_net:.1f}%)",
            icon=":material/remove_circle_outline:",
            use_container_width=True,
            key="btn_sent_net",
            on_click=_set_active_sent,
            args=("Netral",),
        )
    with col_btn3:
        st.button(
            f"SENTIMEN POSITIF  \n{n_pos:,} post ({pct_pos:.1f}%)",
            icon=":material/check_circle_outline:",
            use_container_width=True,
            key="btn_sent_pos",
            on_click=_set_active_sent,
            args=("Positif",),
        )

    selected_sent = st.session_state['active_drilldown_sent']
    df_sent = df[sent_series == selected_sent].copy()

    theme_color = "#EF4444" if selected_sent == "Negatif" else ("#10B981" if selected_sent == "Positif" else "#64748B")
    theme_dark = "#B91C1C" if selected_sent == "Negatif" else ("#047857" if selected_sent == "Positif" else "#334155")
    theme_bg = "#FEF2F2" if selected_sent == "Negatif" else ("#ECFDF5" if selected_sent == "Positif" else "#F8FAFC")
    sent_icon_name = "sentiment_neg" if selected_sent == "Negatif" else ("sentiment_pos" if selected_sent == "Positif" else "sentiment_net")

    eng_sent = int(pd.to_numeric(df_sent.get('total_engagement', 0), errors='coerce').fillna(0).sum()) if not df_sent.empty else 0
    pct_sel = (len(df_sent) / tot_all * 100) if tot_all > 0 else 0.0

    render_html(f"""
    <div style="background:{theme_bg}; border:1px solid {theme_color}35; border-left:4px solid {theme_color}; border-radius:8px; padding:10px 16px; margin:12px 0 18px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:9px; flex-wrap:wrap;">
            {get_ui_icon(sent_icon_name, size=16, color=theme_dark)}
            <span style="font-weight:800; font-size:12.5px; color:{theme_dark}; letter-spacing:0.3px;">FOKUS ANALISIS: SENTIMEN {selected_sent.upper()}</span>
            <span style="color:#475569; font-size:12px;">Menampilkan <strong>{len(df_sent):,}</strong> postingan ({pct_sel:.1f}%) dari total <strong>{tot_all:,}</strong> data korpus.</span>
        </div>
        <div style="font-size:11.5px; font-weight:700; color:#0F2942; background:#FFFFFF; border:1px solid {theme_color}30; padding:3px 10px; border-radius:999px;">
            Total Interaksi: {fmt_val(eng_sent)}
        </div>
    </div>
    """)

    if df_sent.empty:
        st.info(f"Tidak ada postingan bersentimen {selected_sent} pada kombinasi filter saat ini.")
        return

    # Pastikan nama penulis teresolusi bersih (hilangkan nama invisible / Hangul filler)
    auth_series = df_sent['author'].astype(str) if 'author' in df_sent.columns else pd.Series('Anonim', index=df_sent.index)
    handle_series = df_sent['handle'].astype(str) if 'handle' in df_sent.columns else pd.Series('', index=df_sent.index)
    url_series = df_sent['url'].astype(str) if 'url' in df_sent.columns else pd.Series('', index=df_sent.index)
    plat_series = df_sent['platform'].astype(str) if 'platform' in df_sent.columns else pd.Series('Web', index=df_sent.index)

    df_sent['_resolved_author'] = [
        _resolve_author_info(a, h, u, p)
        for a, h, u, p in zip(auth_series, handle_series, url_series, plat_series)
    ]

    # -------------------------------------------------------------
    # BAGIAN A: ISU DOMINAN & WILAYAH TERDAMPAK (2 Kolom)
    # -------------------------------------------------------------
    c_issue, c_region = st.columns([1, 1], gap="medium")

    with c_issue:
        with st.container(border=True):
            render_html(_section_header_html(1, f"Isu Dominan ({selected_sent})", "issue", theme_dark, "Klaster Kebijakan"))
            issue_counts = df_sent['issue_category'].astype(str).value_counts().reset_index()
            issue_counts.columns = ['Klaster Isu', 'Jumlah']

            fig_issue = px.bar(
                issue_counts,
                x='Jumlah',
                y='Klaster Isu',
                orientation='h',
                text='Jumlah',
                color_discrete_sequence=[theme_color]
            )
            fig_issue.update_traces(textposition='outside', cliponaxis=False, marker_line_width=0)
            fig_issue.update_layout(
                yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=11, color='#334155')),
                xaxis=dict(title=None, showgrid=True, gridcolor='#F1F5F9', tickfont=dict(size=10, color='#64748B')),
                margin=dict(l=8, r=42, t=6, b=6),
                height=260,
                font=dict(family='Plus Jakarta Sans, sans-serif'),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_issue, use_container_width=True, config={'displayModeBar': False}, key=f"drill_issue_chart_{selected_sent}")

    with c_region:
        with st.container(border=True):
            reg_color = "#DC2626" if selected_sent == "Negatif" else ("#059669" if selected_sent == "Positif" else "#2563EB")
            render_html(_section_header_html(2, f"Wilayah / Daerah Terdampak ({selected_sent})", "region", reg_color, "Top 7 Wilayah"))
            region_counts = df_sent['detected_region'].astype(str).value_counts().reset_index()
            region_counts.columns = ['Wilayah Terdampak', 'Jumlah']

            fig_region = px.bar(
                region_counts.head(7),
                x='Jumlah',
                y='Wilayah Terdampak',
                orientation='h',
                text='Jumlah',
                color_discrete_sequence=[reg_color]
            )
            fig_region.update_traces(textposition='outside', cliponaxis=False, marker_line_width=0)
            fig_region.update_layout(
                yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=11, color='#334155')),
                xaxis=dict(title=None, showgrid=True, gridcolor='#F1F5F9', tickfont=dict(size=10, color='#64748B')),
                margin=dict(l=8, r=42, t=6, b=6),
                height=260,
                font=dict(family='Plus Jakarta Sans, sans-serif'),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_region, use_container_width=True, config={'displayModeBar': False}, key=f"drill_region_chart_{selected_sent}")

    # Rekomendasi Solusi Prioritas (Khusus Sentimen Negatif)
    if selected_sent == "Negatif" and not issue_counts.empty:
        top_neg_issue = str(issue_counts.iloc[0]['Klaster Isu'])
        neg_count = int(issue_counts.iloc[0]['Jumlah'])
        sol = get_issue_solution(top_neg_issue)
        sol_icon = get_ui_icon("solution", size=14, color="#B91C1C")

        render_html(f"""
        <div style="background:#FFF5F5; border:1px solid #FECACA; border-left:4px solid #DC2626; border-radius:10px; padding:14px 18px; margin:10px 0 18px 0; box-shadow:0 1px 2px rgba(220,38,38,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
                <span style="display:inline-flex; align-items:center; gap:6px; font-size:11px; font-weight:800; color:#991B1B; background:#FEE2E2; border:1px solid #FCA5A5; padding:4px 10px; border-radius:6px; letter-spacing:0.3px;">
                    {sol_icon}
                    <span>SOLUSI PRIORITAS ATAS ISU TERTINGGI: {html.escape(top_neg_issue.upper())} ({neg_count:,} Komplain)</span>
                </span>
                <span style="font-size:11px; font-weight:700; color:#991B1B; background:#FFFFFF; border:1px solid #FECACA; padding:3px 10px; border-radius:999px;">
                    Target Waktu Tanggap (SLA): {html.escape(sol['sla'])}
                </span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px; margin-bottom:8px;">
                <div style="background:#FFFFFF; border:1px solid #FEE2E2; border-radius:6px; padding:8px 10px;">
                    <div style="font-size:10px; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.4px;">Penanggung Jawab</div>
                    <div style="font-size:12px; font-weight:700; color:#0F2942; margin-top:2px;">{html.escape(sol['unit'])}</div>
                </div>
                <div style="background:#FFFFFF; border:1px solid #FEE2E2; border-radius:6px; padding:8px 10px;">
                    <div style="font-size:10px; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.4px;">Fokus Wilayah / Titik Kritis</div>
                    <div style="font-size:12px; font-weight:600; color:#334155; margin-top:2px;">{html.escape(sol['target'])}</div>
                </div>
            </div>
            <div style="background:#FFFFFF; border:1px solid #FEE2E2; border-radius:6px; padding:9px 11px; font-size:12px; color:#1E293B; line-height:1.5;">
                <strong style="color:#991B1B;">Rencana Tindakan Cepat (Solusi):</strong> {html.escape(sol['tindakan'])}
            </div>
        </div>
        """)

    # -------------------------------------------------------------
    # BAGIAN B: PLATFORM PENYEBAR (DENGAN LOGO) & TOP AKUN PEMENGARUH
    # -------------------------------------------------------------
    c_plat, c_acc = st.columns([1, 1], gap="medium")

    with c_plat:
        with st.container(border=True):
            render_html(_section_header_html(3, f"Kanal / Platform Penyebar ({selected_sent})", "channel", "#0F2942", "Sebaran Kanal"))
            plat_counts = df_sent['platform'].astype(str).value_counts().reset_index()
            plat_counts.columns = ['Platform', 'Jumlah']

            plat_color_map = {
                'Instagram': PLATFORM_COLORS.get('instagram', '#E1306C'),
                'Facebook': PLATFORM_COLORS.get('facebook', '#1877F2'),
                'TikTok': PLATFORM_COLORS.get('tiktok', '#111827'),
                'Threads': PLATFORM_COLORS.get('threads', '#334155'),
                'Twitter': PLATFORM_COLORS.get('twitter', '#0F172A'),
                'YouTube': PLATFORM_COLORS.get('youtube', '#FF0000'),
                'News': PLATFORM_COLORS.get('news', '#0284C7'),
            }

            fig_plat = px.pie(
                plat_counts,
                names='Platform',
                values='Jumlah',
                hole=0.56,
                color='Platform',
                color_discrete_map=plat_color_map
            )
            fig_plat.update_traces(textinfo='percent', textfont=dict(size=11))
            fig_plat.update_layout(
                showlegend=False,
                margin=dict(l=8, r=8, t=4, b=4),
                height=178,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(
                    text=f"<b style='font-size:17px;color:#0F2942;'>{len(df_sent):,}</b><br><span style='font-size:10px;color:#64748B;'>Post</span>",
                    x=0.5, y=0.5, showarrow=False
                )]
            )
            st.plotly_chart(fig_plat, use_container_width=True, config={'displayModeBar': False}, key=f"drill_plat_chart_{selected_sent}")

            # Daftar Logo Platform Resmi (Pengganti Legenda Teks / Emoji)
            tot_plat_posts = max(1, int(plat_counts['Jumlah'].sum()))
            plat_pills = []
            for _, pr in plat_counts.iterrows():
                p_name = str(pr['Platform'])
                p_cnt = int(pr['Jumlah'])
                p_pct = p_cnt / tot_plat_posts * 100
                p_logo = get_platform_icon(p_name, size=14)
                plat_pills.append(
                    f'<div style="display:inline-flex; align-items:center; gap:6px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:4px 9px; font-size:11px;">'
                    f'{p_logo}'
                    f'<span style="font-weight:700; color:#0F2942;">{html.escape(p_name)}</span>'
                    f'<span style="color:#64748B; font-weight:600;">{p_cnt:,} ({p_pct:.1f}%)</span>'
                    f'</div>'
                )
            render_html(f'<div style="display:flex; flex-wrap:wrap; gap:6px; padding-top:8px; border-top:1px solid #F1F5F9;">{"".join(plat_pills)}</div>')

    with c_acc:
        with st.container(border=True):
            render_html(_section_header_html(4, f"Top Akun Pemengaruh / Paling Vokal ({selected_sent})", "users", "#0F2942", "Top 5 Engagement"))

            count_col = 'cleaned_content' if 'cleaned_content' in df_sent.columns else ('content' if 'content' in df_sent.columns else '_resolved_author')
            df_sent['_plat_str'] = df_sent['platform'].astype(str)
            acc_grp = df_sent.groupby(['_resolved_author', '_plat_str'], observed=True).agg(
                posts=(count_col, 'count'),
                total_eng=('total_engagement', 'sum')
            ).reset_index().sort_values(by=['total_eng', 'posts'], ascending=[False, False]).head(5)

            acc_rows = []
            for rank, (_, r) in enumerate(acc_grp.iterrows(), 1):
                auth_full = str(r['_resolved_author'])
                plat = str(r['_plat_str'])
                eng = fmt_val(r['total_eng'])
                cnt = int(r['posts'])
                initials = html.escape(_get_initials(auth_full))
                plat_logo = get_platform_icon(plat, size=14)
                acc_rows.append(
                    f'<tr style="border-bottom:1px solid #F1F5F9; font-size:11.5px;">'
                    f'<td style="padding:10px 8px; max-width:190px;">'
                    f'<div style="display:flex; align-items:center; gap:8px; min-width:0;" title="{html.escape(auth_full)}">'
                    f'<span style="width:24px; height:24px; border-radius:50%; background:#0F2942; color:#FFFFFF; font-size:9.5px; font-weight:800; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;">{initials}</span>'
                    f'<span style="font-weight:700; color:#0F2942; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{html.escape(auth_full)}</span>'
                    f'</div>'
                    f'</td>'
                    f'<td style="padding:10px 8px; white-space:nowrap;">'
                    f'<span style="display:inline-flex; align-items:center; gap:6px; color:#334155; font-weight:600;">{plat_logo}<span>{html.escape(plat)}</span></span>'
                    f'</td>'
                    f'<td style="padding:10px 8px; text-align:center;">'
                    f'<span style="background:#EFF6FF; color:#2563EB; font-weight:700; font-size:11px; padding:2px 8px; border-radius:999px;">{cnt:,}</span>'
                    f'</td>'
                    f'<td style="padding:10px 8px; text-align:right; font-weight:800; color:#0F2942; white-space:nowrap;">{eng}</td>'
                    f'</tr>'
                )

            empty_row = '<tr><td colspan="4" style="padding:14px; text-align:center; color:#94A3B8; font-size:12px;">Tidak ada data akun</td></tr>'
            table_html = (
                '<div style="overflow-x:auto; border:1px solid #E2E8F0; border-radius:8px; background:#FFFFFF;">'
                '<table style="width:100%; border-collapse:collapse; table-layout:auto;">'
                '<thead>'
                '<tr style="background:#F8FAFC; border-bottom:1.5px solid #E2E8F0; font-size:10px; font-weight:800; color:#475569; letter-spacing:0.4px;">'
                '<th style="padding:10px 8px; text-align:left;">AKUN / PROFIL</th>'
                '<th style="padding:10px 8px; text-align:left;">PLATFORM</th>'
                '<th style="padding:10px 8px; text-align:center;">POST</th>'
                '<th style="padding:10px 8px; text-align:right;">ENGAGEMENT</th>'
                '</tr>'
                '</thead>'
                f'<tbody>{"".join(acc_rows) if acc_rows else empty_row}</tbody>'
                '</table>'
                '</div>'
            )
            render_html(table_html)

    # -------------------------------------------------------------
    # BAGIAN C: DAFTAR POSTINGAN NYATA (Dengan Logo Platform & Filter)
    # -------------------------------------------------------------
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    render_html(_section_header_html(5, f"Daftar Postingan Nyata ({selected_sent})", "posts", theme_dark, "Top 12 Interaksi"))

    c_search, c_reg = st.columns([1.8, 1.2], vertical_alignment="bottom")
    with c_search:
        search_q = st.text_input(
            f"Cari kata kunci dalam postingan {selected_sent}:",
            placeholder="Ketik topik, kata kunci, wilayah, atau nama akun...",
            key=f"search_drill_{selected_sent}"
        )
    with c_reg:
        reg_options = ["Semua Wilayah Terdampak"] + sorted([str(x) for x in df_sent['detected_region'].dropna().unique()])
        selected_reg_filter = st.selectbox(
            "Filter Wilayah Terdampak:",
            reg_options,
            index=0,
            key=f"drill_reg_select_{selected_sent}"
        )

    df_display = df_sent.copy()
    if selected_reg_filter != "Semua Wilayah Terdampak":
        df_display = df_display[df_display['detected_region'].astype(str) == selected_reg_filter]

    if search_q.strip():
        q_clean = search_q.strip()
        blob = (
            df_display.get('cleaned_content', pd.Series('', index=df_display.index)).fillna('').astype(str) + " "
            + df_display.get('raw_content', pd.Series('', index=df_display.index)).fillna('').astype(str) + " "
            + df_display['_resolved_author'].astype(str) + " "
            + df_display['detected_region'].astype(str)
        )
        df_display = df_display[blob.str.contains(q_clean, case=False, na=False, regex=False)]

    if df_display.empty:
        st.info(f"Tidak ada postingan {selected_sent} yang cocok dengan filter saat ini.")
        return

    st.caption(f"Menampilkan {min(len(df_display), 12):,} dari {len(df_display):,} postingan {selected_sent} terurut berdasarkan interaksi tertinggi.")

    df_sorted = df_display.sort_values(by='total_engagement', ascending=False).head(12)

    cols = st.columns(3)
    pin_svg = get_ui_icon("pin", size=11, color="#2563EB")
    heart_svg = get_ui_icon("heart", size=11, color="#64748B")
    share_svg = get_ui_icon("share", size=11, color="#64748B")
    ext_svg = get_ui_icon("external", size=11, color="#2563EB")

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        c = cols[idx % 3]

        raw_text = str(row.get('raw_content', row.get('cleaned_content', '')))
        sent_badge = str(row.get('sentiment_name', selected_sent))

        s_color = '#10B981' if sent_badge == 'Positif' else ('#EF4444' if sent_badge == 'Negatif' else '#64748B')
        s_bg = '#ECFDF5' if sent_badge == 'Positif' else ('#FEF2F2' if sent_badge == 'Negatif' else '#F8FAFC')

        author_disp = str(row.get('_resolved_author', 'Anonim'))
        initials = html.escape(_get_initials(author_disp))
        platform_name = str(row.get('platform', 'Web'))
        plat_logo = get_platform_icon(platform_name, size=15)

        raw_url = str(row.get('url', '')).strip()
        post_url = raw_url if (raw_url and raw_url.lower() != 'nan' and raw_url.startswith('http')) else "#"

        clean_snip = " ".join(raw_text.split())
        if len(clean_snip) > 165:
            clean_snip = clean_snip[:162].rstrip() + "..."

        likes_val = fmt_val(row.get('likes', 0))
        shares_val = fmt_val(max(row.get('shares', 0), row.get('reposts', 0)))
        date_val = html.escape(str(row.get('date_str', '')))
        reg_val = str(row.get('detected_region', 'Nasional / Terpusat'))

        link_html = (
            f'<a href="{html.escape(post_url)}" target="_blank" rel="noopener noreferrer" '
            f'style="display:inline-flex; align-items:center; gap:4px; color:#2563EB; font-weight:700; '
            f'text-decoration:none; padding:3px 7px; border-radius:5px; background:#EFF6FF; border:1px solid #BFDBFE;">'
            f'<span>Buka</span>{ext_svg}</a>'
            if post_url != '#' else ''
        )

        card_html = (
            f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid {s_color}; border-radius:10px; padding:14px; margin-bottom:14px; box-shadow:0 1px 3px rgba(15,23,42,0.04); min-height:235px; display:flex; flex-direction:column; justify-content:space-between;">'
            f'<div>'
            f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:10px;">'
            f'<div style="display:flex; align-items:center; gap:9px; min-width:0; flex:1;">'
            f'<div style="width:34px; height:34px; border-radius:50%; background:#0F2942; color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; flex-shrink:0;">{initials}</div>'
            f'<div style="min-width:0; flex:1;">'
            f'<div style="font-size:12px; font-weight:700; color:#0F2942; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{html.escape(author_disp)}">{html.escape(author_disp)}</div>'
            f'<div style="display:flex; align-items:center; gap:4px; font-size:10px; color:#2563EB; font-weight:600; margin-top:2px; min-width:0;" title="{html.escape(reg_val)}">'
            f'{pin_svg}<span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{html.escape(reg_val)}</span>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'<div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">'
            f'<span title="{html.escape(platform_name)}" style="display:inline-flex; align-items:center;">{plat_logo}</span>'
            f'<span style="font-size:9.5px; font-weight:800; color:{s_color}; background:{s_bg}; padding:2px 7px; border-radius:4px; border:1px solid {s_color}35; white-space:nowrap;">{html.escape(sent_badge)}</span>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:11.8px; color:#334155; line-height:1.5; margin-bottom:10px;">"{html.escape(clean_snip)}"</div>'
            f'</div>'
            f'<div style="border-top:1px solid #F1F5F9; padding-top:8px; display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#64748B; gap:6px;">'
            f'<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">'
            f'<span style="display:inline-flex; align-items:center; gap:3px;">{heart_svg}<strong style="color:#0F2942;">{likes_val}</strong> Likes</span>'
            f'<span style="color:#CBD5E1;">&bull;</span>'
            f'<span style="display:inline-flex; align-items:center; gap:3px;">{share_svg}<strong style="color:#0F2942;">{shares_val}</strong> Shares</span>'
            f'</div>'
            f'<div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">'
            f'<span>{date_val}</span>'
            f'{link_html}'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        with c:
            render_html(card_html)
