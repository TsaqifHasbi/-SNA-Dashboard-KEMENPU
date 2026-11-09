# Intelligence Platform Slide Renderers Part 3 (Slides 21 - 25)
# Executive Academic Policy Intelligence - Dynamic Data Integration & Unindented HTML

import os
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
from src.clean_header_footer import render_slide_header, render_slide_footer, _chart_layout, render_html, fmt_val
from src.icons import get_platform_icon, get_platform_badge

# Helper for Single Platform Slide
def _render_single_platform_sentiment_slide(df, platform_name, title, breadcrumb):
    render_slide_header(title, breadcrumb)
    df_plat = df[df['platform'].str.lower().str.contains(platform_name.lower())]
    if len(df_plat) == 0:
        df_plat = df
        
    total_plat = len(df_plat)
    u_plat = df_plat['author'].nunique() if total_plat > 0 else 0
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
<div style="font-size:11px; color:#64748B;">{total_plat:,} data riil</div>
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
        # Check if platform has multiple dates or single date
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
            render_html(f"""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:12px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">Top Aktor / Kreator di {platform_name}</div>""")
            top_auth = df_plat['author'].value_counts().head(8)
            auth_rows = []
            for a_name, cnt in top_auth.items():
                auth_rows.append(f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #F1F5F9; font-size:11.5px;">
<span style="color:#0F172A; font-weight:600;">{a_name[:22]}</span>
<span style="font-weight:700; color:#3B82F6;">{cnt:,} post</span>
</div>""")
            render_html("".join(auth_rows))
        
    render_slide_footer()


# SLIDE 21: SENTIMENT INSTAGRAM
def render_slide_sentiment_instagram(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'Instagram', "SENTIMENT: INSTAGRAM",
        f"Analisis Sentimen Platform Instagram &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 22: SENTIMENT YOUTUBE
def render_slide_sentiment_youtube(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'YouTube', "SENTIMENT: YOUTUBE",
        f"Analisis Sentimen Platform YouTube &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 23: SENTIMENT TIKTOK
def render_slide_sentiment_tiktok(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'TikTok', "SENTIMENT: TIKTOK",
        f"Analisis Sentimen Platform TikTok &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 24: SENTIMENT THREADS
def render_slide_sentiment_threads(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_single_platform_sentiment_slide(
        df, 'Threads', "SENTIMENT: THREADS",
        f"Analisis Sentimen Platform Threads &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 25: EMOTION ANALYSIS /1 (Plutchik 8 Dimensions Distribution & Intensity)
def _generate_svg_donut(items, total_val, size=215, stroke_width=26):
    import math
    r = (size - stroke_width - 8) / 2
    c = 2 * math.pi * r
    cx = size / 2
    cy = size / 2
    
    total = sum(x['count'] for x in items) if sum(x['count'] for x in items) > 0 else 1
    
    circles = []
    accum = 0
    for it in items:
        if it['count'] <= 0:
            continue
        pct = it['count'] / total
        dash = pct * c
        space = c - dash
        offset = -accum
        gap = 1.5 if len(items) > 1 else 0
        dash_fill = max(0, dash - gap)
        space_fill = space + gap
        circles.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{it["color"]}" '
            f'stroke-width="{stroke_width}" stroke-dasharray="{dash_fill:.2f} {space_fill:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        accum += dash
        
    circles_html = "".join(circles)
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="display:block; flex-shrink:0;">'
        f'{circles_html}'
        f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" font-size="19" font-weight="800" fill="#0F172A" font-family="Plus Jakarta Sans, sans-serif">{total_val}</text>'
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#64748B" font-family="Plus Jakarta Sans, sans-serif">afektif</text>'
        f'</svg>'
    )
    return svg


def render_slide_emotion_analysis_1(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("EMOTION ANALYSIS /1", f"Distribusi & Intensitas 8 Emosi (IndoBERT Plutchik) &bull; {topic_label} &bull; {date_str}")
    
    total_all = len(df) if len(df) > 0 else 1
    # Filter for affective emotions (Plutchik basic emotions)
    df_emo = df[~df['emotion'].str.lower().isin(['netral', 'neutral', 'informatif', 'informational'])]
    if df_emo.empty:
        df_emo = df
        
    total_emo = len(df_emo)
    emo_counts = df_emo['emotion'].value_counts()
    
    # Standard 8 Plutchik Emotions mapping (matching Standar Eksekutif palette & icons)
    PLUTCHIK_8 = [
        {'key': 'Senang', 'en': 'Joy', 'emoji': '🙂', 'color': '#F59E0B', 'type': 'pos'},
        {'key': 'Marah', 'en': 'Anger', 'emoji': '😠', 'color': '#F87171', 'type': 'neg'},
        {'key': 'Takut', 'en': 'Fear', 'emoji': '😨', 'color': '#8B5CF6', 'type': 'neg'},
        {'key': 'Percaya', 'en': 'Trust', 'emoji': '🤝', 'color': '#10B981', 'type': 'pos'},
        {'key': 'Jijik', 'en': 'Disgust', 'emoji': '🤢', 'color': '#84CC16', 'type': 'neg'},
        {'key': 'Antisipasi', 'en': 'Anticipation', 'emoji': '⏳', 'color': '#F97316', 'type': 'pos'},
        {'key': 'Terkejut', 'en': 'Surprise', 'emoji': '😲', 'color': '#06B6D4', 'type': 'neu'},
        {'key': 'Sedih', 'en': 'Sadness', 'emoji': '😢', 'color': '#3B82F6', 'type': 'neg'},
    ]
    
    results = []
    for item in PLUTCHIK_8:
        cnt = int(emo_counts.get(item['key'], 0) + emo_counts.get(item['en'], 0))
        pct = round(cnt / total_emo * 100) if total_emo > 0 else 0
        results.append({**item, 'count': cnt, 'pct': pct})
        
    # Sort ranking by count descending
    results.sort(key=lambda x: x['count'], reverse=True)
    
    top_emo = results[0]
    pos_pct = sum(r['pct'] for r in results if r['type'] == 'pos')
    neg_pct = sum(r['pct'] for r in results if r['type'] == 'neg')

    # ROW 1: 4 Executive KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:86px; display:flex; flex-direction:column; justify-content:space-between;">
<div style="font-size:10.5px; font-weight:700; color:#64748B; letter-spacing:0.5px;">TOTAL MENTIONS</div>
<div style="font-size:26px; font-weight:800; color:#0F172A; line-height:1;">{fmt_val(total_all)}</div>
<div style="font-size:10.5px; color:#64748B;">{fmt_val(total_emo)} afektif &bull; {fmt_val(total_all - total_emo)} netral</div>
</div>""")
        
    with c2:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:86px; display:flex; flex-direction:column; justify-content:space-between;">
<div style="font-size:10.5px; font-weight:700; color:#64748B; letter-spacing:0.5px;">DOMINANT EMOTION</div>
<div style="font-size:22px; font-weight:800; color:{top_emo['color']}; line-height:1; display:flex; align-items:center; gap:8px;">
<span>{top_emo['emoji']}</span> <span>{top_emo['en']}</span>
</div>
<div style="font-size:10.5px; color:#64748B;">{top_emo['pct']}% of classified mentions</div>
</div>""")
        
    with c3:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:86px; display:flex; flex-direction:column; justify-content:space-between;">
<div style="font-size:10.5px; font-weight:700; color:#64748B; letter-spacing:0.5px;">POSITIVE EMOTIONS</div>
<div style="font-size:26px; font-weight:800; color:#10B981; line-height:1;">{pos_pct}%</div>
<div style="font-size:10.5px; color:#64748B;">Joy &bull; Trust &bull; Anticipation</div>
</div>""")
        
    with c4:
        render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:86px; display:flex; flex-direction:column; justify-content:space-between;">
<div style="font-size:10.5px; font-weight:700; color:#64748B; letter-spacing:0.5px;">NEGATIVE EMOTIONS</div>
<div style="font-size:26px; font-weight:800; color:#EF4444; line-height:1;">{neg_pct}%</div>
<div style="font-size:10.5px; color:#64748B;">Anger &bull; Fear &bull; Sadness &bull; Disgust</div>
</div>""")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    
    # ROW 2: 2 Main Cards (Snug padding, relative bar scaling)
    col_left, col_right = st.columns([1.05, 1.25])
    
    active_items = [r for r in results if r['count'] > 0]
    if not active_items:
        active_items = results
        
    max_count = max(r['count'] for r in active_items) if active_items else 1
    
    with col_left:
        # EMOTION DISTRIBUTION CARD (Tight padding, crisp balance)
        svg_donut = _generate_svg_donut(active_items, fmt_val(total_emo), size=170, stroke_width=22)
        
        legend_rows = []
        for r in active_items:
            legend_rows.append(f"""<div style="display:flex; align-items:center; gap:8px;">
<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{r['color']}; flex-shrink:0;"></span>
<span style="font-size:11.5px; font-weight:700; color:#475569; width:28px; text-align:right;">{r['pct']}%</span>
<span style="font-size:11.5px; font-weight:600; color:#0F172A; display:flex; align-items:center; gap:5px;">
<span>{r['emoji']}</span> <span>{r['en']}</span>
</span>
</div>""")
            
        left_card_html = f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:260px; display:flex; flex-direction:column; justify-content:space-between;">
<div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
<div style="font-size:13px; font-weight:800; color:#0F172A; letter-spacing:0.3px;">EMOTION DISTRIBUTION</div>
<div style="font-size:11px; font-weight:600; color:#64748B;">{fmt_val(total_emo)} mentions</div>
</div>
<div style="font-size:10px; color:#94A3B8;">{topic_label} &mdash; All Sources &mdash; {date_str}</div>
</div>

<div style="display:flex; align-items:center; justify-content:center; gap:16px; padding:4px 0; margin-top:2px;">
{svg_donut}
<div style="display:flex; flex-direction:column; justify-content:center; gap:4px; flex-shrink:0;">
{''.join(legend_rows)}
</div>
</div>
</div>"""
        render_html(left_card_html)
        
    with col_right:
        # EMOTION INTENSITY RANKING CARD (Scaled relative to maximum count so bars fill width naturally)
        ranking_rows = []
        for r in active_items:
            rel_w = max(4, round((r['count'] / max_count) * 100))
            ranking_rows.append(f"""<div style="display:flex; align-items:center; margin-bottom:4px;">
<div style="width:96px; display:flex; align-items:center; gap:5px; font-size:11.5px; font-weight:600; color:#334155; flex-shrink:0;">
<span>{r['emoji']}</span> <span>{r['en']}</span>
</div>
<div style="flex:1; height:11px; background:#EEF2F6; border-radius:999px; overflow:hidden; margin:0 10px;">
<div style="width:{rel_w}%; height:100%; background:{r['color']}; border-radius:999px; transition:width 0.3s ease;"></div>
</div>
<div style="width:34px; text-align:right; font-size:10.5px; font-weight:600; color:#64748B; flex-shrink:0;">
{fmt_val(r['count'])}
</div>
<div style="width:32px; text-align:right; font-size:11px; font-weight:700; color:#0F172A; flex-shrink:0;">
{r['pct']}%
</div>
</div>""")
            
        right_card_html = f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 15px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:260px; display:flex; flex-direction:column; justify-content:space-between;">
<div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
<div style="font-size:13px; font-weight:800; color:#0F172A; letter-spacing:0.3px;">EMOTION INTENSITY RANKING</div>
<div style="font-size:10.5px; font-weight:600; color:#94A3B8;">by mention count</div>
</div>
<div style="font-size:10px; color:#94A3B8;">{topic_label} &mdash; All Sources &mdash; {date_str}</div>
</div>

<div style="display:flex; flex-direction:column; justify-content:center; padding:4px 0; margin-top:2px;">
{''.join(ranking_rows)}
</div>
</div>"""
        render_html(right_card_html)
        
    render_slide_footer()
