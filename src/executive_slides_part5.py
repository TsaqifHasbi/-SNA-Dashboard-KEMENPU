# Intelligence Platform Slide Renderers Part 5 (Slides 33 - 37)
# Top Influencers per Platform (Facebook, Instagram, YouTube, TikTok, Threads)
# Executive Academic Policy Intelligence - Dynamic Data Integration & Unindented HTML

import os
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
from src.clean_header_footer import render_slide_header, render_slide_footer, _chart_layout, render_html, fmt_val
from src.icons import get_platform_icon, get_platform_badge

def _render_platform_influencers_slide(df, platform_name, title, breadcrumb_sub):
    render_slide_header(title, breadcrumb_sub)
    
    df_plat = df[df['platform'].str.lower().str.contains(platform_name.lower())]
    if df_plat.empty: df_plat = df
    
    top_actors = df_plat.groupby('author').agg(
        mentions=('raw_content', 'count'),
        engagement=('total_engagement', 'sum') if 'total_engagement' in df_plat.columns else ('raw_content', 'count'),
        likes=('likes', 'sum') if 'likes' in df_plat.columns else ('raw_content', 'count'),
        sentiment=('sentiment_name', lambda s: s.value_counts().index[0])
    ).reset_index().sort_values('mentions', ascending=False).head(20)
    
    col_scat, col_cards = st.columns([1.7, 1.3])
    
    with col_scat:
        with st.container(border=True):
            render_html(f"""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">
Matriks Interest vs Power: Top Aktor di {platform_name}
</div>""")
            fig = go.Figure()
            sent_colors = {'Positif': '#10B981', 'Netral': '#64748B', 'Negatif': '#EF4444'}
            
            for row in top_actors.itertuples():
                col = sent_colors.get(row.sentiment, '#64748B')
                clean_name = f"@{str(row.author).strip().lstrip('@')}"
                fig.add_trace(go.Scatter(
                    x=[row.mentions], y=[row.engagement],
                    mode='markers+text',
                    marker=dict(size=14, color=col, line=dict(color='#FFFFFF', width=1.5)),
                    text=[clean_name[:14]], textposition='top center',
                    textfont=dict(size=10, family='Plus Jakarta Sans', color='#1E293B'),
                    name=clean_name
                ))
                
            fig.update_layout(showlegend=False, **_chart_layout(height=380))
            fig.update_xaxes(title="Volume Konten (Interest)")
            fig.update_yaxes(title="Total Engagement (Power)")
            st.plotly_chart(fig, use_container_width=True)
        
    with col_cards:
        with st.container(border=True):
            render_html(f"""<div style="font-size:13px; font-weight:800; color:#1E293B; margin-bottom:12px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">
TOP 5 AKUN PALING BERPENGARUH DI {platform_name.upper()}
</div>""")
            top5 = top_actors.head(5)
        cards = []
        for idx, row in enumerate(top5.itertuples(), 1):
            s_col = '#10B981' if row.sentiment == 'Positif' else ('#EF4444' if row.sentiment == 'Negatif' else '#64748B')
            clean_name = f"@{str(row.author).strip().lstrip('@')}"
            cards.append(f"""<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
<div>
<div style="font-size:12px; font-weight:700; color:#0F172A;">{idx}. {clean_name[:22]}</div>
<div style="font-size:10.5px; color:#64748B; margin-top:2px;">{row.mentions:,} post &bull; {fmt_val(row.engagement)} total eng</div>
</div>
<span style="font-size:10px; font-weight:700; color:{s_col}; background:#FFFFFF; padding:3px 8px; border-radius:4px; border:1px solid {s_col}40;">
{row.sentiment}
</span>
</div>""")
        render_html("".join(cards) + "</div>")
        
    render_slide_footer()


# SLIDE 33: FACEBOOK
def render_slide_top_influencers_facebook(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_platform_influencers_slide(
        df, "Facebook", "TOP INFLUENCERS: FACEBOOK",
        f"Matriks Aktor Utama &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 34: INSTAGRAM
def render_slide_top_influencers_instagram(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_platform_influencers_slide(
        df, "Instagram", "TOP INFLUENCERS: INSTAGRAM",
        f"Matriks Aktor Utama &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 35: YOUTUBE
def render_slide_top_influencers_youtube(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_platform_influencers_slide(
        df, "YouTube", "TOP INFLUENCERS: YOUTUBE",
        f"Matriks Aktor Utama &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 36: TIKTOK
def render_slide_top_influencers_tiktok(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_platform_influencers_slide(
        df, "TikTok", "TOP INFLUENCERS: TIKTOK",
        f"Matriks Aktor Utama &bull; {topic_label} &bull; {date_str}"
    )

# SLIDE 37: THREADS
def render_slide_top_influencers_threads(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_platform_influencers_slide(
        df, "Threads", "TOP INFLUENCERS: THREADS",
        f"Matriks Aktor Utama &bull; {topic_label} &bull; {date_str}"
    )
