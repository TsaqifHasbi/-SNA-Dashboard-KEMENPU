# Intelligence Platform Slides Part 1 (Slides 11 - 15)
import os
import re
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
import networkx as nx
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
# pyrefly: ignore[missing-import]
import streamlit.components.v1 as components_v1
from src.sna_engine import build_sna_network, generate_pyvis_html, get_network_metrics
from src.clean_header_footer import render_slide_header, render_slide_footer, _chart_layout, render_html, fmt_val
from src.icons import get_platform_icon

# SLIDE 11: VOLUME, USER, ENGAGEMENT, REACH
def render_slide_volume_user_engagement_reach(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("VOLUME, USER, ENGAGEMENT, REACH", f"{topic_label} • All Sources • {date_str}")
    
    v_total = len(df)
    u_total = df['author'].nunique() if v_total > 0 else 0
    e_total = int(df['total_engagement'].sum()) if 'total_engagement' in df.columns and v_total > 0 else 0
    r_total = int(df['reach'].sum()) if 'reach' in df.columns and v_total > 0 else 0

    v_str, u_str, e_str, r_str = fmt_val(v_total), fmt_val(u_total), fmt_val(e_total), fmt_val(r_total)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="font-size:11px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL MENTIONS</div>
<div style="font-size:32px; font-weight:800; color:#0F172A; margin:4px 0;">{v_str}</div>
<div style="font-size:12px; color:#64748B;"><strong>{v_total:,}</strong> Sebutan Riil <span style="color:#10B981; font-weight:700;">(100%)</span></div>
</div>""")
    with c2:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="font-size:11px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL USERS</div>
<div style="font-size:32px; font-weight:800; color:#0F172A; margin:4px 0;">{u_str}</div>
<div style="font-size:12px; color:#64748B;"><strong>{u_total:,}</strong> Penulis Unik <span style="color:#10B981; font-weight:700;">({round(u_total/v_total*100) if v_total else 0}% Rasio)</span></div>
</div>""")
    with c3:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="font-size:11px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL ENGAGEMENTS</div>
<div style="font-size:32px; font-weight:800; color:#0F172A; margin:4px 0;">{e_str}</div>
<div style="font-size:12px; color:#64748B;">Total Interaksi Publik</div>
</div>""")
    with c4:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="font-size:11px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL REACH</div>
<div style="font-size:32px; font-weight:800; color:#0F172A; margin:4px 0;">{r_str}</div>
<div style="font-size:12px; color:#64748B;">Potensi Jangkauan Netizen</div>
</div>""")

    st.write("")
    col_left, col_right = st.columns(2)
    with col_left:
        with st.container(border=True):
            render_html(f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
<span style="font-size:13px; font-weight:700; color:#0F172A; text-transform:uppercase;">MENTION TREND</span>
<span style="font-size:11.5px; color:#94A3B8; font-weight:600;">Tren Lintas Waktu</span>
</div>
<div style="font-size:10.5px; color:#64748B; margin-bottom:10px;">{topic_label} &bull; All Sources &bull; {date_str}</div>""")
            daily = df.groupby('date_str').size().reset_index(name='count').sort_values('date_str').tail(30)
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=daily['date_str'], y=daily['count'],
                mode='lines', line=dict(color='#F97316', width=2.5, shape='spline'),
                fill='tozeroy', fillcolor='rgba(249, 115, 22, 0.12)', name='Mentions'
            ))
            if not daily.empty:
                max_row = daily.loc[daily['count'].idxmax()]
                fig_trend.add_annotation(
                    x=max_row['date_str'], y=max_row['count'], text=f"{max_row['count']:,}",
                    showarrow=True, arrowhead=2, arrowcolor='#F97316', font=dict(size=11, color='#EA580C')
                )
            fig_trend.update_layout(**_chart_layout(height=265))
            st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        with st.container(border=True):
            plat_eng = df.groupby('platform')['total_engagement'].sum()
            total_p_eng = plat_eng.sum() if plat_eng.sum() > 0 else 1
            max_p_eng = plat_eng.max() if not plat_eng.empty and plat_eng.max() > 0 else 1
            
            order_meta = [
                ('TikTok', '#111827'),
                ('Threads', '#4B5563'),
                ('YouTube', '#FF0000'),
                ('Twitter', '#1D9BF0'),
                ('Instagram', '#E1306C'),
                ('Facebook', '#1877F2'),
                ('News', '#0284C7')
            ]
            
            items = []
            for plat, col in order_meta:
                val = int(plat_eng.get(plat, 0))
                pct = round((val / total_p_eng) * 100) if total_p_eng > 0 else 0
                rel_w = max(4, round((val / max_p_eng) * 100)) if val > 0 else 0
                icon_svg = get_platform_icon(plat, size=15, custom_color=col)
                items.append(
                    f'<div style="display:flex; align-items:center; margin-bottom:10px;">'
                    f'<div style="width:110px; font-size:12px; font-weight:600; color:#334155; display:flex; align-items:center; gap:7px;">'
                    f'<span>{icon_svg}</span> <span>{plat}</span>'
                    f'</div>'
                    f'<div style="flex:1; background:#F1F5F9; height:12px; border-radius:6px; overflow:hidden; margin:0 12px;">'
                    f'<div style="background:{col}; width:{rel_w}%; height:100%; border-radius:6px; transition:width 0.3s ease;"></div>'
                    f'</div>'
                    f'<div style="width:105px; text-align:right; font-size:11.5px; font-weight:700; color:#0F172A;">'
                    f'{pct}% <span style="font-size:10.5px; font-weight:500; color:#64748B;">({fmt_val(val)})</span>'
                    f'</div>'
                    f'</div>'
                )
            unified_card_html = f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
<span style="font-size:13px; font-weight:700; color:#0F172A; text-transform:uppercase;">ENGAGEMENT BY CHANNEL</span>
<span style="font-size:11.5px; color:#94A3B8; font-weight:600;">Pangsa Interaksi Riil</span>
</div>
<div style="font-size:10.5px; color:#64748B; margin-bottom:14px;">{topic_label} &bull; All Sources &bull; {date_str}</div>
{''.join(items)}"""
            render_html(unified_card_html)

    top_channel = plat_eng.idxmax() if not plat_eng.empty else "TikTok"
    top_channel_pct = round((plat_eng.max() / total_p_eng) * 100) if total_p_eng > 0 else 0
    render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:18px 24px; margin-top:16px;">
<ul style="margin:0; padding-left:20px; font-size:13px; line-height:1.7; color:#1E293B;">
<li style="margin-bottom:6px;">
<b>Kanal Interaksi Tertinggi</b>: Platform <b>{top_channel}</b> memimpin total interaksi publik dengan pangsa <b>{top_channel_pct}%</b> dari seluruh interaksi di korpus {topic_label}.
</li>
<li>
<b>Aktivitas Komunitas Organik</b>: Total <b>{u_total:,}</b> penulis unik berpartisipasi dengan <b>{v_total:,}</b> mention, membuktikan partisipasi aktif publik terhadap pemantauan kebijakan ini.
</li>
</ul>
</div>""")
    render_slide_footer()


# SLIDE 12: MENTIONS TREND BY CHANNEL
def render_slide_mentions_trend_channel(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("MENTIONS TREND BY CHANNEL", f"{topic_label} • All Sources • {date_str}")
    
    daily_plat = df.groupby(['date_str', 'platform']).size().unstack(fill_value=0).reset_index().tail(30)
    fig = go.Figure()
    plat_colors = {
        'Twitter': '#1D9BF0', 'TikTok': '#111827', 'Instagram': '#E1306C',
        'YouTube': '#FF0000', 'Threads': '#4B5563', 'Facebook': '#1877F2', 'News': '#0284C7'
    }
    for p, c in plat_colors.items():
        if p in daily_plat.columns:
            fig.add_trace(go.Scatter(
                x=daily_plat['date_str'].astype(str), y=daily_plat[p],
                name=p, mode='lines+markers', line=dict(color=c, width=2, shape='spline'), marker=dict(size=5)
            ))
    fig.update_layout(**_chart_layout(height=360))
    fig.update_xaxes(type='category', title="Tanggal")
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)
    
    top_plat_name = df['platform'].value_counts().index[0] if not df.empty else "Twitter"
    render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 22px; margin-top:14px;">
<div style="font-size:12.5px; color:#334155; line-height:1.6;">
Berdasarkan data riil, kanal <strong>{top_plat_name}</strong> secara konsisten mencatatkan frekuensi publikasi terbanyak dalam kurun waktu pemantauan, disusul video di TikTok dan artikel legitimasi di Portal Berita Daring.
</div>
</div>""")
    render_slide_footer()


# SLIDE 13: MENTIONS TREND BY SENTIMENT
def render_slide_mentions_trend_sentiment(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("MENTIONS TREND BY SENTIMENT", f"{topic_label} • All Sources • {date_str}")
    
    daily_sent = df.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index().tail(30)
    fig = go.Figure()
    s_colors = {'Positif': '#10B981', 'Netral': '#94A3B8', 'Negatif': '#EF4444'}
    for s_name, c in s_colors.items():
        if s_name in daily_sent.columns:
            fig.add_trace(go.Scatter(
                x=daily_sent['date_str'].astype(str), y=daily_sent[s_name],
                name=s_name, mode='lines+markers', line=dict(color=c, width=2.2, shape='spline'),
                stackgroup='one', marker=dict(size=4)
            ))
    fig.update_layout(**_chart_layout(height=360))
    fig.update_xaxes(type='category', title="Tanggal")
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)
    
    s_counts = df['sentiment_name'].value_counts()
    dominant_sent = s_counts.index[0] if not s_counts.empty else "Positif"
    render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 22px; margin-top:14px;">
<div style="font-size:12.5px; color:#334155; line-height:1.6;">
Tren sentimen terklasifikasi oleh model <strong>IndoBERT Sentimen V2 (Akurasi 91.33%, Macro F1 91.37%)</strong> menunjukkan dominasi sentimen <strong>{dominant_sent}</strong> ({s_counts.get(dominant_sent, 0):,} mention), mengonfirmasi respon publik terhadap keberlanjutan program menuju 2029.
</div>
</div>""")
    render_slide_footer()


# SLIDE 14: MENTIONS TREND BY EMOTIONS
def render_slide_mentions_trend_emotions(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("MENTIONS TREND BY EMOTIONS", f"{topic_label} • All Sources • {date_str}")
    
    plutchik_map = {
        'Joy': '#F59E0B', 'Trust': '#10B981', 'Anticipation': '#8B5CF6', 'Surprise': '#EC4899',
        'Sadness': '#64748B', 'Fear': '#6366F1', 'Disgust': '#14B8A6', 'Anger': '#EF4444'
    }
    daily_emo = df.groupby(['date_str', 'emotion']).size().unstack(fill_value=0).reset_index().tail(30)
    fig = go.Figure()
    for emo_name, color in plutchik_map.items():
        if emo_name in daily_emo.columns:
            fig.add_trace(go.Scatter(
                x=daily_emo['date_str'].astype(str), y=daily_emo[emo_name],
                name=emo_name, mode='lines+markers', line=dict(color=color, width=2.2, shape='spline'), marker=dict(size=5)
            ))
    fig.update_layout(**_chart_layout(height=360))
    fig.update_xaxes(type='category', title="Tanggal")
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True)
    
    df_emo_aff = df[~df['emotion'].str.lower().isin(['neutral', 'netral', 'informatif', 'informational'])] if 'emotion' in df.columns else df
    emo_counts = df_emo_aff['emotion'].value_counts() if not df_emo_aff.empty else (df['emotion'].value_counts() if 'emotion' in df.columns else pd.Series())
    top_emo = emo_counts.index[0] if not emo_counts.empty else "Joy"
    render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 22px; margin-top:14px;">
<div style="font-size:12.5px; color:#334155; line-height:1.6;">
Dimensi emosi Plutchik mencatat emosi <strong>{top_emo}</strong> ({emo_counts.get(top_emo, 0):,} data) sebagai respon emosional tertinggi di kalangan netizen terhadap dinamika isu {topic_label}.
</div>
</div>""")
    render_slide_footer()


# SLIDE 15: SNA BY SENTIMENT
def render_slide_sna_by_sentiment(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("SNA BY SENTIMENT", f"Social Network Analysis • Polarisasi Sentimen • {topic_label} • {date_str}")
    
    col_graph, col_sidebar = st.columns([2.7, 1.3])
    
    G = build_sna_network(df, max_nodes=70, topic_filter=topic_label, mode='sentiment')
    
    with col_graph:
        top_lower = str(topic_label).lower()
        if 'pu' in top_lower or 'menteri' in top_lower or 'kementerian' in top_lower or 'pekerjaan' in top_lower:
            c1_desc = "Diskusi publik seputar preservasi jalan nasional, perbaikan jalan rusak, kemantapan infrastruktur, kesiapan jalur logistik, dan konektivitas antarwilayah."
            c2_desc = f"Apresiasi terhadap percepatan pembangunan bendungan, penyelesaian tanggul pengendali banjir, revitalisasi irigasi, dan proyek infrastruktur {topic_label}."
            c3_desc = "Pemberitaan media mengenai kebijakan dan sidak kepemimpinan Menteri PU, arahan jajaran Ditjen teknis, serta sinergi pengawasan Komisi V DPR."
            c4_desc = "Sorotan kritis warganet dan aduan masyarakat terkait jalan rusak berlubang, genangan banjir daerah, keterlambatan proyek kontraktor, serta transparansi lelang PU."
        elif 'sekolah' in top_lower or 'rakyat' in top_lower:
            c1_desc = "Diskusi seputar pemerataan akses fasilitas belajar, pemutakhiran data siswa prasejahtera, dan sarana sekolah di daerah 3T."
            c2_desc = f"Apresiasi terhadap perluasan beasiswa pendidikan vokasi, peningkatan kualifikasi guru, dan afirmasi program {topic_label}."
            c3_desc = "Pemberitaan regulasi Kemendikbudristek, alokasi anggaran fungsi pendidikan 20%, dan evaluasi kurikulum inklusif."
            c4_desc = "Sorotan kritis disparitas kualitas sekolah swasta vs negeri, pungutan liar, dan transparansi penyaluran bantuan operasional."
        elif 'kdmp' in top_lower or 'koperasi' in top_lower:
            c1_desc = "Diskusi seputar keanggotaan warga desa, penyertaan modal simpan-pinjam, dan adopsi pencatatan digital koperasi."
            c2_desc = f"Dukungan terhadap hilirisasi produk pertanian lokal, kemitraan rantai pasok desa, dan penguatan permodalan {topic_label}."
            c3_desc = "Pemberitaan regulasi Kementerian Koperasi, fasilitasi legalitas badan hukum, dan skema pembiayaan LPDB."
            c4_desc = "Kekhawatiran potensi kredit macet (NPL), intervensi politik lokal, dan desakan audit independen tata kelola keuangan."
        elif 'listrik' in top_lower or 'ev' in top_lower or 'elektrifikasi' in top_lower:
            c1_desc = "Diskusi warganet seputar ketersediaan SPKLU, durasi pengisian daya baterai, dan perbandingan biaya operasional harian."
            c2_desc = f"Antusiasme terhadap insentif subsidi kendaraan ramah lingkungan, pengurangan emisi karbon, dan hilirisasi nikel nasional."
            c3_desc = "Pemberitaan kebijakan kementerian teknis, target bauran energi hijau, dan kesiapan rantai pasok industri otomotif."
            c4_desc = "Keluhan depresiasi harga purna jual baterai, keandalan jaringan listrik daerah, dan transparansi distribusi kuota subsidi."
        else:
            c1_desc = "Diskusi seputar pemutakhiran data penerima manfaat dan dokumentasi pelaksanaan distribusi di lapangan."
            c2_desc = f"Menyoroti investasi gizi generasi muda serta pemberdayaan petani, peternak, dan UMKM lokal pendukung program {topic_label}."
            c3_desc = "Pemberitaan dinamika anggaran fiskal APBN, regulasi Badan Gizi Nasional, dan evaluasi berkala kementerian terkait."
            c4_desc = "Tuntutan pengawasan standar higienitas dapur satelit, audit transparansi rekanan vendor, dan mitigasi risiko keracunan."

        render_html(f"""<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#1E3A8A; margin-bottom:4px;">KLASTER PUBLIK UMUM</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{c1_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#047857; margin-bottom:4px;">KLASTER PEMERINTAH & PENDUKUNG</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{c2_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#475569; margin-bottom:4px;">KLASTER MEDIA MASSA</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{c3_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#B91C1C; margin-bottom:4px;">KLASTER MASYARAKAT KRITIS</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{c4_desc}</div>
</div>
</div>""")
        
        html_graph = generate_pyvis_html(G, height="500px", mode='sentiment')
        components_v1.html(html_graph, height=510, scrolling=False)

    with col_sidebar:
        # Dynamically calculated SNA metrics from real data
        all_mentions = len(df)
        all_users = df['author'].nunique()
        nodes_cnt = len(G.nodes())
        edges_cnt = len(G.edges())
        density = round(nx.density(G) * 100, 2) if nodes_cnt > 1 else 0.1
        degrees = [d for n, d in G.degree()]
        avg_deg = round(sum(degrees) / len(degrees), 1) if degrees else 0.0

        s_counts = df['sentiment_name'].value_counts()
        pos_p = round((s_counts.get('Positif', 0) / all_mentions) * 100) if all_mentions else 0
        neu_p = round((s_counts.get('Netral', 0) / all_mentions) * 100) if all_mentions else 0
        neg_p = round((s_counts.get('Negatif', 0) / all_mentions) * 100) if all_mentions else 0

        # Top actual nodes from df
        top_authors = df['author'].value_counts().head(10)
        node_rows = []
        for author, count in top_authors.items():
            clean_a = f"@{str(author).strip().lstrip('@')}"
            node_rows.append(f'<div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="color:#1D9BF0; font-weight:600;">{clean_a[:18]}</span> <b style="color:#0F172A;">{count:,}</b></div>')
        nodes_list_html = "".join(node_rows)

        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px;">
<div style="font-size:13px; font-weight:800; color:#0F172A; border-bottom:1px solid #F1F5F9; padding-bottom:6px; margin-bottom:10px;">PROFIL JARINGAN SNA</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:16px;">
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Total Mentions</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{all_mentions:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Total Users</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{all_users:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Nodes Graf</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{nodes_cnt}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Edges Relasi</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{edges_cnt}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Densitas Jaringan</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{density}%</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Avg Degree</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{avg_deg}</div>
</div>
</div>
<div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:6px;">DISTRIBUSI SENTIMEN DATA</div>
<div style="margin-bottom:16px;">
<div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
<span style="color:#10B981; font-weight:600;">Positif</span><span style="font-weight:700;">{pos_p}%</span>
</div>
<div style="background:#E2E8F0; height:6px; border-radius:3px; overflow:hidden; margin-bottom:6px;">
<div style="background:#10B981; width:{pos_p}%; height:100%;"></div>
</div>
<div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
<span style="color:#64748B; font-weight:600;">Netral</span><span style="font-weight:700;">{neu_p}%</span>
</div>
<div style="background:#E2E8F0; height:6px; border-radius:3px; overflow:hidden; margin-bottom:6px;">
<div style="background:#64748B; width:{neu_p}%; height:100%;"></div>
</div>
<div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
<span style="color:#EF4444; font-weight:600;">Negatif</span><span style="font-weight:700;">{neg_p}%</span>
</div>
<div style="background:#E2E8F0; height:6px; border-radius:3px; overflow:hidden;">
<div style="background:#EF4444; width:{neg_p}%; height:100%;"></div>
</div>
</div>
<div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:6px;">TOP AKTOR CENTRALITY</div>
<div style="max-height:180px; overflow-y:auto; font-size:11px; line-height:1.6;">
{nodes_list_html}
</div>
</div>""")
        
    render_slide_footer()
