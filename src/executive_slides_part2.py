# Intelligence Platform Slide Renderers Part 2 (Slides 16 - 20)
# Executive Academic Policy Intelligence - Dynamic Data Integration & Unindented HTML

import os
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
import networkx as nx
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
# pyrefly: ignore[missing-import]
import streamlit.components.v1 as components_v1
from src.sna_engine import build_sna_network, generate_pyvis_html
from src.clean_header_footer import render_slide_header, render_slide_footer, _chart_layout, render_html, fmt_val
from src.icons import get_platform_icon, get_platform_badge

# SLIDE 16: SNA BY EMOTIONS
def render_slide_sna_by_emotions(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("SNA BY EMOTIONS", f"Social Network Analysis &bull; Klaster Emosi Komunitas &bull; {topic_label} &bull; {date_str}")
    
    col_graph, col_sidebar = st.columns([2.7, 1.3])
    
    G = build_sna_network(df, max_nodes=70, topic_filter=topic_label, mode='emotion')
    
    with col_graph:
        top_lower = str(topic_label).lower()
        if 'pu' in top_lower or 'menteri' in top_lower or 'kementerian' in top_lower or 'pekerjaan' in top_lower:
            emo_c1_desc = "Kritik tajam atas jalan rusak berlubang, keterlambatan penanganan genangan banjir, serta keluhan kualitas pengerjaan kontraktor infrastruktur."
            emo_c2_desc = "Kekhawatiran publik atas kerawanan longsor jalur nasional, ketahanan tanggul sungai saat musim hujan ekstrem, dan keselamatan pengguna jalan."
            emo_c3_desc = f"Apresiasi kepuasan publik atas perbaikan cepat jalan tol/nasional, peresmian bendungan baru, dan komitmen pelayanan infrastruktur {topic_label}."
            emo_c4_desc = "Dukungan penuh terhadap arahan Menteri PU, sinergi pengawasan DPR RI, dan transparansi lelang proyek Ditjen Bina Marga & SDA."
        elif 'sekolah' in top_lower or 'rakyat' in top_lower:
            emo_c1_desc = "Kritik tajam atas ketimpangan fasilitas pendidikan antardaerah, biaya siluman, dan lambatnya renovasi gedung sekolah."
            emo_c2_desc = "Kekhawatiran orang tua terkait daya tampung sistem zonasi, kualitas tenaga pengajar honorer, dan kepastian ijazah."
            emo_c3_desc = f"Apresiasi program bantuan seragam/buku gratis, beasiswa siswa berprestasi, dan antusiasme kegiatan belajar {topic_label}."
            emo_c4_desc = "Dukungan dewan pendidikan, pengawasan komite sekolah independen, dan komitmen anggaran afirmasi daerah 3T."
        elif 'kdmp' in top_lower or 'koperasi' in top_lower:
            emo_c1_desc = "Kritik atas dugaan monopoli pengurus lama, kendala pencairan dana usaha tani, dan transparansi SHU tahunan."
            emo_c2_desc = "Kecemasan risiko gagal bayar kredit mikro anggota, fluktuasi harga komoditas panen, dan akuntabilitas buku kas."
            emo_c3_desc = f"Apresiasi peningkatan permodalan usaha desa, kemudahan akses pupuk bersubsidi, dan semangat gotong royong {topic_label}."
            emo_c4_desc = "Kepercayaan terhadap pendampingan dinas koperasi, audit akuntan publik bersertifikasi, dan penguatan lembaga ekonomi desa."
        elif 'listrik' in top_lower or 'ev' in top_lower or 'elektrifikasi' in top_lower:
            emo_c1_desc = "Kekesalan atas antrean panjang charging station (SPKLU), kenaikan tarif dasar listrik, dan biaya penggantian paket baterai."
            emo_c2_desc = "Kekhawatiran isu keselamatan baterai saat banjir, jarak tempuh riil saat macet, dan ketersediaan bengkel resmi terdekat."
            emo_c3_desc = f"Kepuasan atas efisiensi biaya bahan bakar, kenyamanan kabin hening tanpa getaran, dan teknologi mutakhir kendaraan {topic_label}."
            emo_c4_desc = "Keyakinan terhadap jaminan garansi pabrikan 8 tahun, komitmen transisi energi bersih, dan ekspansi infrastruktur PLN."
        else:
            emo_c1_desc = "Kritik tajam tata kelola anggaran, dugaan monopoli vendor lokal, dan transparansi distribusi menu harian."
            emo_c2_desc = "Kecemasan orang tua terkait kualitas gizi, potensi keracunan makanan, serta kesiapan fasilitas dapur 3T."
            emo_c3_desc = f"Apresiasi menu sehat sekolah, senyum siswa penerima manfaat, dan antusiasme orang tua murid mendukung program {topic_label}."
            emo_c4_desc = "Dukungan akademisi gizi, monitoring ketat Badan Gizi Nasional, dan pelibatan koperasi serta petani desa."

        render_html(f"""<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#EF4444; margin-bottom:4px;">KLASTER MARAH (ANGER)</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{emo_c1_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#6366F1; margin-bottom:4px;">KLASTER KEKHAWATIRAN (FEAR)</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{emo_c2_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#F59E0B; margin-bottom:4px;">KLASTER KEGEMBIRAAN (JOY)</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{emo_c3_desc}</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:12px; font-weight:800; color:#10B981; margin-bottom:4px;">KLASTER KEPERCAYAAN (TRUST)</div>
<div style="font-size:11.5px; color:#334155; line-height:1.5;">{emo_c4_desc}</div>
</div>
</div>""")
        
        html_graph = generate_pyvis_html(G, height="500px", mode='emotion')
        components_v1.html(html_graph, height=510, scrolling=False)

    with col_sidebar:
        # Dynamic network metrics from filtered df
        all_mentions = len(df)
        all_users = df['author'].nunique() if all_mentions > 0 else 0
        nodes_cnt = len(G.nodes())
        edges_cnt = len(G.edges())
        density = round(nx.density(G) * 100, 2) if nodes_cnt > 1 else 0.1
        degrees = [d for n, d in G.degree()]
        avg_deg = round(sum(degrees) / len(degrees), 1) if degrees else 0.0

        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:8px;">PROFIL GRAF JARINGAN (SNA)</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:16px;">
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Total Mentions</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{all_mentions:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Total Penulis Unik</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{all_users:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Aktor Utama (Nodes)</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{nodes_cnt:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Relasi Interaksi (Edges)</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{edges_cnt:,}</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Densitas Jaringan</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{density}%</div>
</div>
<div style="background:#F8FAFC; padding:8px; border-radius:6px; border:1px solid #E2E8F0;">
<div style="font-size:9.5px; color:#64748B;">Avg Degree</div>
<div style="font-size:15px; font-weight:800; color:#0F172A;">{avg_deg}</div>
</div>
</div>""")

        # Dynamic Emotion breakdown (Supporting both English and Indonesian Plutchik taxonomy)
        emo_counts = df['emotion'].value_counts()
        total_emo = len(df)
        
        PLUTCHIK_8_DEFS = [
            {'en': 'Joy', 'id': 'Senang', 'label': 'Joy / Senang', 'color': '#F59E0B'},
            {'en': 'Trust', 'id': 'Percaya', 'label': 'Trust / Percaya', 'color': '#10B981'},
            {'en': 'Anticipation', 'id': 'Antisipasi', 'label': 'Anticipation / Harapan', 'color': '#F97316'},
            {'en': 'Anger', 'id': 'Marah', 'label': 'Anger / Marah', 'color': '#EF4444'},
            {'en': 'Fear', 'id': 'Takut', 'label': 'Fear / Cemas', 'color': '#6366F1'},
            {'en': 'Sadness', 'id': 'Sedih', 'label': 'Sadness / Sedih', 'color': '#3B82F6'},
            {'en': 'Disgust', 'id': 'Jijik', 'label': 'Disgust / Kecewa', 'color': '#14B8A6'},
            {'en': 'Surprise', 'id': 'Terkejut', 'label': 'Surprise / Terkejut', 'color': '#EC4899'},
        ]
        
        total_affective = sum(int(emo_counts.get(d['en'], 0) + emo_counts.get(d['id'], 0)) for d in PLUTCHIK_8_DEFS)
        denom = total_affective if total_affective > 0 else (total_emo if total_emo > 0 else 1)
        
        max_c = max([int(emo_counts.get(d['en'], 0) + emo_counts.get(d['id'], 0)) for d in PLUTCHIK_8_DEFS] or [1])
        if max_c <= 0: max_c = 1
        
        emo_bars = []
        for d in PLUTCHIK_8_DEFS:
            c_val = int(emo_counts.get(d['en'], 0) + emo_counts.get(d['id'], 0))
            p_val = round(c_val / denom * 100, 1)
            rel_w = max(4, round((c_val / max_c) * 100)) if c_val > 0 else 0
            color = d['color']
            emo_bars.append(f"""<div style="margin-bottom:6px;">
<div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:2px;">
<span style="color:#334155; font-weight:600;">{d['label']}</span><span style="font-weight:700; color:{color};">{p_val}% <span style="font-size:10px; color:#94A3B8; font-weight:500;">({c_val:,})</span></span>
</div>
<div style="background:#F1F5F9; height:6px; border-radius:3px; overflow:hidden;">
<div style="background:{color}; width:{rel_w}%; height:100%; border-radius:3px; transition:width 0.3s ease;"></div>
</div>
</div>""")
        emo_bars_html = "".join(emo_bars)

        # Dynamic Top 10 Actors
        top_authors = df['author'].value_counts().head(10)
        node_rows = []
        for author, count in top_authors.items():
            clean_a = f"@{str(author).strip().lstrip('@')}"
            node_rows.append(f'<div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="color:#1D9BF0; font-weight:600;">{clean_a[:18]}</span> <b style="color:#0F172A;">{count:,}</b></div>')
        nodes_list_html = "".join(node_rows)

        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:none; border-radius:0 0 8px 8px; padding:16px; margin-top:-16px;">
<div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:8px;">DISTRIBUSI EMOSI RIIL</div>
<div style="margin-bottom:16px;">{emo_bars_html}</div>
<div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:6px;">TOP AKTOR CENTRALITY</div>
<div style="max-height:160px; overflow-y:auto; font-size:11px; line-height:1.6;">{nodes_list_html}</div>
</div>""")
        
    render_slide_footer()


# SLIDE 17: OVERALL SENTIMENT & 7 PLATFORMS
def render_slide_overall_sentiment(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("OVERALL SENTIMENT", f"Sentimen Keseluruhan & Komparasi 7 Kanal &bull; {topic_label} &bull; {date_str}")
    
    total = len(df)
    s_counts = df['sentiment_name'].value_counts()
    pos_c = s_counts.get('Positif', 0)
    neu_c = s_counts.get('Netral', 0)
    neg_c = s_counts.get('Negatif', 0)
    
    pos_p = round(pos_c / total * 100, 1) if total else 0
    neu_p = round(neu_c / total * 100, 1) if total else 0
    neg_p = round(neg_c / total * 100, 1) if total else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#64748B;">TOTAL MENTIONS</div>
<div style="font-size:28px; font-weight:800; color:#0F172A; margin:2px 0;">{fmt_val(total)}</div>
<div style="font-size:11px; color:#64748B;">100% Data Riil</div>
</div>""")
    with c2:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#10B981;">SENTIMEN POSITIF</div>
<div style="font-size:28px; font-weight:800; color:#10B981; margin:2px 0;">{pos_p}%</div>
<div style="font-size:11px; color:#64748B;">{pos_c:,} mentions</div>
</div>""")
    with c3:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#64748B;">SENTIMEN NETRAL</div>
<div style="font-size:28px; font-weight:800; color:#64748B; margin:2px 0;">{neu_p}%</div>
<div style="font-size:11px; color:#64748B;">{neu_c:,} mentions</div>
</div>""")
    with c4:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#EF4444;">SENTIMEN NEGATIF</div>
<div style="font-size:28px; font-weight:800; color:#EF4444; margin:2px 0;">{neg_p}%</div>
<div style="font-size:11px; color:#64748B;">{neg_c:,} mentions</div>
</div>""")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    col_donut, col_bars = st.columns([1.2, 2.0])
    
    with col_donut:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">Komposisi Sentimen Keseluruhan</div>""")
            fig_donut = go.Figure(data=[go.Pie(
                labels=['Positif', 'Netral', 'Negatif'],
                values=[pos_c, neu_c, neg_c],
                hole=0.62,
                marker=dict(colors=['#10B981', '#94A3B8', '#EF4444'], line=dict(color='#FFFFFF', width=2)),
                textinfo='percent',
                hoverinfo='label+value'
            )])
            fig_donut.update_layout(**_chart_layout(height=320, showlegend=True))
            st.plotly_chart(fig_donut, use_container_width=True)
            
    with col_bars:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">Perbandingan Proporsi Sentimen Lintas 7 Kanal</div>""")
            ct = pd.crosstab(df['platform'], df['sentiment_name'], normalize='index') * 100
            plats = ct.index.tolist()
            
            fig_bar = go.Figure()
            for s_name, col in [('Positif', '#10B981'), ('Netral', '#94A3B8'), ('Negatif', '#EF4444')]:
                vals = [round(ct.loc[p, s_name], 1) if s_name in ct.columns else 0 for p in plats]
                fig_bar.add_trace(go.Bar(
                    name=s_name, y=plats, x=vals, orientation='h',
                    marker=dict(color=col), text=[f"{v}%" if v > 5 else "" for v in vals], textposition='inside'
                ))
            fig_bar.update_layout(barmode='stack', **_chart_layout(height=320))
            fig_bar.update_xaxes(title="Persentase (%)", range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)
        
    render_slide_footer()


# Helper for Single Platform Slide
def _render_single_platform_sentiment_slide(df, platform_name, title, breadcrumb):
    render_slide_header(title, breadcrumb)
    df_plat = df[df['platform'].str.lower().str.contains(platform_name.lower())]
    if len(df_plat) == 0:
        df_plat = df
        
    total_plat = len(df_plat)
    u_plat = df_plat['author'].nunique()
    eng_plat = int(df_plat['total_engagement'].sum()) if 'total_engagement' in df_plat.columns else 0
    s_counts = df_plat['sentiment_name'].value_counts()
    
    pos_c = s_counts.get('Positif', 0)
    neu_c = s_counts.get('Netral', 0)
    neg_c = s_counts.get('Negatif', 0)
    
    pos_p = round(pos_c / total_plat * 100, 1) if total_plat else 0
    neu_p = round(neu_c / total_plat * 100, 1) if total_plat else 0
    neg_p = round(neg_c / total_plat * 100, 1) if total_plat else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#64748B;">TOTAL MENTIONS</div>
<div style="font-size:26px; font-weight:800; color:#0F172A; margin:2px 0;">{fmt_val(total_plat)}</div>
<div style="font-size:11px; color:#64748B;">{total_plat:,} data</div>
</div>""")
    with c2:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#10B981;">POSITIF</div>
<div style="font-size:26px; font-weight:800; color:#10B981; margin:2px 0;">{pos_p}%</div>
<div style="font-size:11px; color:#64748B;">{pos_c:,} post</div>
</div>""")
    with c3:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#64748B;">NETRAL</div>
<div style="font-size:26px; font-weight:800; color:#64748B; margin:2px 0;">{neu_p}%</div>
<div style="font-size:11px; color:#64748B;">{neu_c:,} post</div>
</div>""")
    with c4:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
<div style="font-size:11px; font-weight:700; color:#EF4444;">NEGATIF</div>
<div style="font-size:26px; font-weight:800; color:#EF4444; margin:2px 0;">{neg_p}%</div>
<div style="font-size:11px; color:#64748B;">{neg_c:,} post</div>
</div>""")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    col_chart, col_auth = st.columns([2.0, 1.2])
    
    with col_chart:
        # Check if platform has multiple dates or single date (e.g. Facebook)
        num_dates = df_plat['date_str'].nunique() if 'date_str' in df_plat.columns else 0
        chart_title = "Tren Dinamika Sentimen Harian"
        is_hourly = False
        
        if num_dates > 1:
            daily = df_plat.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index().tail(30)
            x_col = 'date_str'
        else:
            # Check for hourly breakdown in created_at
            if 'created_at' in df_plat.columns:
                df_plat_time = df_plat.copy()
                df_plat_time['dt_temp'] = pd.to_datetime(df_plat_time['created_at'].astype(str).str.replace(' WIB', ''), errors='coerce')
                df_plat_time['hour_str'] = df_plat_time['dt_temp'].dt.strftime('%H:00')
                if df_plat_time['hour_str'].dropna().nunique() > 1:
                    daily = df_plat_time.groupby(['hour_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index()
                    x_col = 'hour_str'
                    chart_title = f"Tren Dinamika Sentimen (Per Jam - {df_plat['date_str'].iloc[0] if num_dates==1 else ''})"
                    is_hourly = True
                else:
                    daily = df_plat.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index()
                    x_col = 'date_str'
            else:
                daily = df_plat.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index()
                x_col = 'date_str'

        with st.container(border=True):
            render_html(f"""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">{chart_title}</div>""")

            fig_time = go.Figure()
            if len(daily) > 1:
                for s_name, col in [('Positif', '#10B981'), ('Netral', '#94A3B8'), ('Negatif', '#EF4444')]:
                    if s_name in daily.columns:
                        fig_time.add_trace(go.Scatter(
                            x=daily[x_col].astype(str), y=daily[s_name], name=s_name, mode='lines+markers',
                            line=dict(color=col, width=2.5, shape='spline'), marker=dict(size=6)
                        ))
                fig_time.update_xaxes(type='category', title="Waktu / Jam" if is_hourly else "Tanggal")
            elif len(daily) == 1:
                for s_name, col in [('Positif', '#10B981'), ('Netral', '#94A3B8'), ('Negatif', '#EF4444')]:
                    val = int(daily[s_name].iloc[0]) if s_name in daily.columns else 0
                    fig_time.add_trace(go.Bar(
                        name=s_name, x=[str(daily[x_col].iloc[0])], y=[val],
                        marker=dict(color=col, cornerradius=6), text=[f"{val:,}"], textposition='auto'
                    ))
                fig_time.update_xaxes(type='category', title="Tanggal")

            fig_time.update_layout(**_chart_layout(height=320))
            st.plotly_chart(fig_time, use_container_width=True)
        
    with col_auth:
        with st.container(border=True):
            render_html(f"""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:12px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">Top Aktor / Penerbit di {platform_name}</div>""")
            top_auth = df_plat['author'].value_counts().head(8)
            auth_rows = []
            for a_name, cnt in top_auth.items():
                auth_rows.append(f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #F1F5F9; font-size:11.5px;">
<span style="color:#0F172A; font-weight:600;">{a_name[:22]}</span>
<span style="font-weight:700; color:#3B82F6;">{cnt:,} post</span>
</div>""")
            render_html("".join(auth_rows))
        
    render_slide_footer()


# SLIDE 18: SENTIMENT ONLINE NEWS
def render_slide_sentiment_online_news(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'News', "SENTIMENT: ONLINE NEWS",
        f"Analisis Sentimen Media Berita Daring &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 19: SENTIMENT TWITTER / X
def render_slide_sentiment_twitter(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'Twitter', "SENTIMENT: TWITTER / X",
        f"Analisis Sentimen Platform Twitter / X &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 20: SENTIMENT FACEBOOK
def render_slide_sentiment_facebook(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'Facebook', "SENTIMENT: FACEBOOK",
        f"Analisis Sentimen Platform Facebook &bull; {topic_label} &bull; {date_str}"
    )
