"""
Tab Analisis Sentimen Terpadu & Deteksi Wilayah Terdampak
===========================================================
Mengintegrasikan 5 Pilar Analisis per Sentimen:
1. Isu Dominan (Top Klaster Isu)
2. Daerah Terdampak (Deteksi Wilayah/Provinsi/Balai PU)
3. Platform Media & Sosial (Distribusi Kanal)
4. Akun Pemengaruh (Top Influencers / Penyebar Utama)
5. Postingan Nyata (Daftar Kartu Postingan dengan Filter & Tautan Asli)
"""

import re
import html
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from src.sentiment_corrector import correct_sentiment
from src.icons import get_platform_icon

# Gazetteer Wilayah & Locus Proyek / Balai PU
REGION_GAZETTEER = [
    ("Sumatera", r"\b(?:sumatera|sumut|sumbar|sumsel|medan|padang|aceh|riau|pekanbaru|palembang|lampung|jambi|bengkulu|geurutee|danau\s+toba|toba|samosir|deli\s+serdang|langkat|asahan|batang\s+toru|bws\s+sumatera|bpjn\s+aceh|bpjn\s+sumut|bpjn\s+sumbar|bpjn\s+riau|bbpjn\s+sumatera)\b"),
    ("DKI Jakarta & Sekitarnya", r"\b(?:jakarta|jaksel|jaktim|jakbar|jakpus|jakut|pattimura|monas|ciliwung|cisadane|kebon\s+pala|kampung\s+melayu|kp\s+melayu|mrt\s+jakarta|lrt\s+jakarta|transjakarta|bbws\s+ciliwung|bbpjn\s+dki)\b"),
    ("Jawa Barat & Banten", r"\b(?:jabar|jawa\s+barat|bandung|bogor|depok|bekasi|banten|tangerang|tangsel|cirebon|sukabumi|citarum|cisadane|serang|lebak|pandeglang|karawang|purwakarta|subang|majalengka|kuningan|bbws\s+citarum|bbpjn\s+dki-jabar|bpjn\s+banten)\b"),
    ("Jawa Tengah & Pantura", r"\b(?:jateng|jawa\s+tengah|semarang|demak|kudus|solo|surakarta|pantura|pemali\s+juana|bengawan\s+solo|pekalongan|brebes|banyumas|purwokerto|cilacap|kebumen|magelang|klaten|sukoharjo|wonogiri|karanganyar|sragen|grobogan|pati|rembang|blora|temanggung|kendal|batang|bbws\s+bengawan\s+solo|bbws\s+pemali\s+juana|bbpjn\s+jateng)\b"),
    ("D.I. Yogyakarta", r"\b(?:jogja|yogyakarta|diy|kulon\s+progo|sleman|bantul|gunungkidul|jjls|progo|opak|merapi|bbws\s+serayu\s+opak|bbpjn\s+jateng-diy)\b"),
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

def extract_affected_region(text):
    if not text or pd.isna(text):
        return "Nasional / Terpusat"
    t = str(text).lower()
    for reg, pat in REGION_GAZETTEER:
        if re.search(pat, t):
            return reg
    return "Nasional / Terpusat"

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

def render_tab_sentiment_drilldown(df_filtered, **kwargs):
    """
    Menampilkan tab eksplorasi sentimen multi-dimensi secara interaktif.
    """
    if df_filtered.empty:
        st.warning("Tidak ada data yang tersedia untuk filter saat ini.")
        return

    df = df_filtered.copy()

    # Pastikan daerah terdeteksi
    if 'detected_region' not in df.columns:
        df['detected_region'] = df['cleaned_content'].apply(extract_affected_region)
    if 'issue_category' not in df.columns:
        df['issue_category'] = df['cleaned_content'].apply(extract_issue_category)

    st.markdown("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:16px 20px; margin-bottom:18px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <span style="background:#0F2942; color:#FFFFFF; font-size:10px; font-weight:800; padding:3px 8px; border-radius:4px; letter-spacing:0.5px;">EKSPLORASI SENTIMEN MULTIDIMENSI</span>
                <h3 style="margin:6px 0 2px 0; color:#0F2942; font-size:18px; font-weight:800;">Analisis Isu, Post, Akun, Platform & Wilayah Terdampak</h3>
                <p style="margin:0; font-size:12px; color:#64748B;">Pilih kategori sentimen untuk membedah secara mendalam isu dominan, peta daerah terdampak, top influencer, dan postingan aslinya.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Selector Sentimen Utama
    tot_all = len(df)
    n_neg = int((df['sentiment_name'] == 'Negatif').sum())
    n_net = int((df['sentiment_name'] == 'Netral').sum())
    n_pos = int((df['sentiment_name'] == 'Positif').sum())

    pct_neg = (n_neg / tot_all * 100) if tot_all > 0 else 0
    pct_net = (n_net / tot_all * 100) if tot_all > 0 else 0
    pct_pos = (n_pos / tot_all * 100) if tot_all > 0 else 0

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    # State switcher
    if 'active_drilldown_sent' not in st.session_state:
        st.session_state['active_drilldown_sent'] = 'Negatif'

    with col_btn1:
        if st.button(f"🔴 SENTIMEN NEGATIF\n{n_neg:,} ({pct_neg:.1f}%)", use_container_width=True, key="btn_sent_neg"):
            st.session_state['active_drilldown_sent'] = 'Negatif'
    with col_btn2:
        if st.button(f"⚪ SENTIMEN NETRAL\n{n_net:,} ({pct_net:.1f}%)", use_container_width=True, key="btn_sent_net"):
            st.session_state['active_drilldown_sent'] = 'Netral'
    with col_btn3:
        if st.button(f"🟢 SENTIMEN POSITIF\n{n_pos:,} ({pct_pos:.1f}%)", use_container_width=True, key="btn_sent_pos"):
            st.session_state['active_drilldown_sent'] = 'Positif'

    selected_sent = st.session_state['active_drilldown_sent']
    
    # Filter dataset sesuai sentimen terpilih
    df_sent = df[df['sentiment_name'] == selected_sent].copy()
    if df_sent.empty:
        df_sent = df

    theme_color = "#EF4444" if selected_sent == "Negatif" else ("#10B981" if selected_sent == "Positif" else "#64748B")
    theme_bg = "#FEF2F2" if selected_sent == "Negatif" else ("#ECFDF5" if selected_sent == "Positif" else "#F8FAFC")

    st.markdown(f"""
    <div style="background:{theme_bg}; border-left:4px solid {theme_color}; border-radius:6px; padding:10px 14px; margin:14px 0 20px 0;">
        <span style="font-weight:800; font-size:13px; color:{theme_color};">FOKUS ANALISIS: SENTIMEN {selected_sent.upper()}</span>
        <span style="color:#475569; font-size:12px; margin-left:8px;">Menampilkan {len(df_sent):,} postingan dari total {tot_all:,} data korpus.</span>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # BAGIAN A: ISU APA & DAERAH MANA (2 Kolom)
    # -------------------------------------------------------------
    c_issue, c_region = st.columns([1, 1], gap="medium")

    with c_issue:
        st.markdown(f"#### 📌 1. Isu Dominan ({selected_sent})")
        issue_counts = df_sent['issue_category'].value_counts().reset_index()
        issue_counts.columns = ['Klaster Isu', 'Jumlah']
        
        fig_issue = px.bar(
            issue_counts,
            x='Jumlah',
            y='Klaster Isu',
            orientation='h',
            text='Jumlah',
            color_discrete_sequence=[theme_color]
        )
        fig_issue.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=20, t=10, b=10),
            height=260,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_issue, use_container_width=True, config={'displayModeBar': False})

    with c_region:
        st.markdown(f"#### 🗺️ 2. Wilayah / Daerah Terdampak ({selected_sent})")
        region_counts = df_sent['detected_region'].value_counts().reset_index()
        region_counts.columns = ['Wilayah Terdampak', 'Jumlah']
        
        fig_region = px.bar(
            region_counts.head(7),
            x='Jumlah',
            y='Wilayah Terdampak',
            orientation='h',
            text='Jumlah',
            color_discrete_sequence=["#2563EB" if selected_sent != "Negatif" else "#DC2626"]
        )
        fig_region.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=20, t=10, b=10),
            height=260,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_region, use_container_width=True, config={'displayModeBar': False})

    # Tampilkan Rekomendasi Solusi Kebijakan Dinamis (Khusus jika menganalisis Isu Negatif)
    if selected_sent == "Negatif" and not issue_counts.empty:
        top_neg_issue = issue_counts.iloc[0]['Klaster Isu']
        neg_count = issue_counts.iloc[0]['Jumlah']
        sol = get_issue_solution(top_neg_issue)
        
        st.markdown(f"""
        <div style="background:#FFF5F5; border:1px solid #FED7D7; border-left:4px solid #E53E3E; border-radius:8px; padding:12px 16px; margin:12px 0 16px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">
                <span style="font-size:11px; font-weight:800; color:#C53030; background:#FED7D7; padding:2px 8px; border-radius:4px;">💡 SOLUSI PRIORITAS ATAS ISU TERTINGGI: {top_neg_issue.upper()} ({neg_count:,} Komplain)</span>
                <span style="font-size:10.5px; font-weight:700; color:#742A2A;">Target Waktu Tanggap (SLA): {sol['sla']}</span>
            </div>
            <div style="font-size:11.5px; color:#2D3748; line-height:1.5; margin-bottom:4px;">
                <strong>Penanggung Jawab:</strong> {sol['unit']}
            </div>
            <div style="font-size:11.5px; color:#2D3748; line-height:1.5; margin-bottom:4px;">
                <strong>Rencana Tindakan Cepat (Solusi):</strong> {sol['tindakan']}
            </div>
            <div style="font-size:10.5px; color:#718096;">
                <strong>Fokus Wilayah / Titik Kritis:</strong> {sol['target']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # BAGIAN B: PLATFORM APA & AKUN APA (2 Kolom)
    # -------------------------------------------------------------
    st.markdown("---")
    c_plat, c_acc = st.columns([1, 1], gap="medium")

    with c_plat:
        st.markdown(f"#### 📱 3. Kanal / Platform Penyebar ({selected_sent})")
        plat_counts = df_sent['platform'].value_counts().reset_index()
        plat_counts.columns = ['Platform', 'Jumlah']
        
        fig_plat = px.pie(
            plat_counts,
            names='Platform',
            values='Jumlah',
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_plat.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=240,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_plat, use_container_width=True, config={'displayModeBar': False})

    with c_acc:
        st.markdown(f"#### 👤 4. Top Akun Pemengaruh / Paling Vokal ({selected_sent})")
        
        # Kelompokkan per author
        count_col = 'cleaned_content' if 'cleaned_content' in df_sent.columns else ('content' if 'content' in df_sent.columns else 'author')
        acc_grp = df_sent.groupby(['author', 'platform'], observed=True).agg(
            posts=(count_col, 'count'),
            total_eng=('total_engagement', 'sum')
        ).reset_index().sort_values(by='total_eng', ascending=False).head(5)
        
        acc_rows = []
        for _, r in acc_grp.iterrows():
            auth = str(r['author'])[:22]
            plat = str(r['platform'])
            eng = fmt_val(r['total_eng'])
            cnt = r['posts']
            acc_rows.append(f"""
            <tr style="border-bottom:1px solid #F1F5F9; font-size:11.5px;">
                <td style="padding:6px 8px; font-weight:700; color:#0F2942;">{auth}</td>
                <td style="padding:6px 8px; color:#64748B;">{plat}</td>
                <td style="padding:6px 8px; text-align:center; color:#2563EB; font-weight:600;">{cnt:,}</td>
                <td style="padding:6px 8px; text-align:right; font-weight:700; color:#0F2942;">{eng}</td>
            </tr>
            """)
            
        st.markdown(f"""
        <table style="width:100%; border-collapse:collapse; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; overflow:hidden;">
            <thead>
                <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; font-size:10.5px; font-weight:800; color:#475569;">
                    <th style="padding:7px 8px; text-align:left;">AKUN / PROFIL</th>
                    <th style="padding:7px 8px; text-align:left;">PLATFORM</th>
                    <th style="padding:7px 8px; text-align:center;">POST</th>
                    <th style="padding:7px 8px; text-align:right;">ENGAGEMENT</th>
                </tr>
            </thead>
            <tbody>
                {"".join(acc_rows) if acc_rows else '<tr><td colspan="4" style="padding:10px; text-align:center; color:#94A3B8;">Tidak ada data</td></tr>'}
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # BAGIAN C: POST APA (Daftar Postingan Nyata dengan Filter Daerah)
    # -------------------------------------------------------------
    st.markdown("---")
    c_head1, c_head2 = st.columns([2, 1], vertical_alignment="center")
    with c_head1:
        st.markdown(f"#### 📝 5. Daftar Postingan Nyata ({selected_sent})")
    with c_head2:
        # Filter tambahan: Pilih Daerah Terdampak Spesifik
        reg_options = ["Semua Wilayah Terdampak"] + sorted([str(x) for x in df_sent['detected_region'].dropna().unique()])
        selected_reg_filter = st.selectbox(
            "Filter Wilayah Terdampak:",
            reg_options,
            index=0,
            key=f"drill_reg_select_{selected_sent}"
        )

    df_display = df_sent.copy()
    if selected_reg_filter != "Semua Wilayah Terdampak":
        df_display = df_display[df_display['detected_region'] == selected_reg_filter]

    # Search filter teks
    search_q = st.text_input(
        f"Cari kata kunci dalam postingan {selected_sent}:",
        placeholder="Ketik topik, kata, atau akun...",
        key=f"search_drill_{selected_sent}"
    )
    if search_q.strip():
        df_display = df_display[df_display['cleaned_content'].astype(str).str.contains(search_q.strip(), case=False, na=False, regex=False)]

    st.caption(f"Menampilkan {min(len(df_display), 12):,} dari {len(df_display):,} postingan {selected_sent} terurut berdasarkan interaksi.")

    # Sort descending by engagement
    df_sorted = df_display.sort_values(by='total_engagement', ascending=False).head(12)

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        c = cols[idx % 3]
        
        raw_text = str(row.get('raw_content', row.get('cleaned_content', '')))
        curr_sent = str(row.get('sentiment_name', selected_sent))
        curr_score = float(row.get('sentiment_score', 0.0))
        
        # Koreksi presisi tertinggi
        sent_badge, _, _, _ = correct_sentiment(raw_text, curr_sent, curr_score)
        
        s_color = '#10B981' if sent_badge == 'Positif' else ('#EF4444' if sent_badge == 'Negatif' else '#64748B')
        s_bg = '#ECFDF5' if sent_badge == 'Positif' else ('#FEF2F2' if sent_badge == 'Negatif' else '#F8FAFC')
        
        author = str(row.get('author', 'Anonim')).strip()
        if not author.startswith('@') and row.get('platform') in ['Twitter', 'Instagram', 'Threads', 'TikTok']:
            author = f"@{author}"
        author = author[:22]

        platform_name = str(row.get('platform', 'Web'))
        raw_url = str(row.get('url', '')).strip()
        post_url = raw_url if (raw_url and raw_url != 'nan' and raw_url.startswith('http')) else "#"
        
        clean_snip = " ".join(raw_text.split())
        if len(clean_snip) > 165:
            clean_snip = clean_snip[:162] + "..."
            
        likes_val = fmt_val(row.get('likes', 0))
        shares_val = fmt_val(max(row.get('shares', 0), row.get('reposts', 0)))
        date_val = str(row.get('date_str', ''))
        reg_val = str(row.get('detected_region', 'Nasional'))
        
        with c:
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:230px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:32px; height:32px; border-radius:50%; background:#0F2942; color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800;">
                                {author[:2].upper().replace('@', '')}
                            </div>
                            <div style="overflow:hidden;">
                                <div style="font-size:11.5px; font-weight:700; color:#0F2942; line-height:1.2; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">
                                    {author}
                                </div>
                                <div style="font-size:9.5px; color:#2563EB; font-weight:600;">
                                    📍 {reg_val[:20]}
                                </div>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:4px;">
                            <span style="font-size:9.5px; font-weight:800; color:{s_color}; background:{s_bg}; padding:2px 6px; border-radius:4px; border:1px solid {s_color}35;">
                                {sent_badge}
                            </span>
                        </div>
                    </div>
                    <div style="font-size:11.5px; color:#334155; line-height:1.5; margin-bottom:10px;">
                        "{clean_snip}"
                    </div>
                </div>
                <div style="border-top:1px solid #F1F5F9; padding-top:8px; display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#64748B;">
                    <div>
                        <span style="font-weight:700; color:#0F2942;">{likes_val}</span> Likes &bull; 
                        <span style="font-weight:700; color:#0F2942;">{shares_val}</span> Shares
                    </div>
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span>{date_val}</span>
                        {"<a href='" + post_url + "' target='_blank' style='color:#2563EB; font-weight:700; text-decoration:none; padding:2px 5px; border-radius:4px; background:#EFF6FF;'>Buka ↗</a>" if post_url != '#' else ''}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
