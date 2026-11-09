# Intelligence Platform Slide Renderers Part 6 (Slides 39 - 47)
# Viral Content Cards per Platform (Twitter/X, Facebook, Instagram, YouTube, TikTok, Threads)
# Executive Academic Policy Intelligence - Dynamic Data Integration & Unindented HTML

import os
import urllib.parse
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
from src.clean_header_footer import render_slide_header, render_slide_footer, render_html, fmt_val
from src.icons import get_platform_icon
from src.sentiment_corrector import correct_sentiment

def _get_profile_url(platform_name, author, handle):
    clean_handle = str(handle or '').strip().lstrip('@')
    clean_author = str(author or '').strip().lstrip('@')
    plat = str(platform_name or '').lower()
    
    if 'twitter' in plat or plat == 'x':
        h = clean_handle or clean_author
        return f"https://x.com/{h}" if h else "https://x.com"
    elif 'threads' in plat:
        h = clean_handle or clean_author
        return f"https://www.threads.net/@{h}" if h else "https://www.threads.net"
    elif 'instagram' in plat:
        h = clean_handle or clean_author
        return f"https://www.instagram.com/{h}/" if h else "https://www.instagram.com"
    elif 'tiktok' in plat:
        h = clean_handle or clean_author
        return f"https://www.tiktok.com/@{h}" if h else "https://www.tiktok.com"
    elif 'youtube' in plat:
        if clean_handle.startswith('UC'):
            return f"https://www.youtube.com/channel/{clean_handle}"
        h = clean_handle or clean_author.replace(' ', '')
        return f"https://www.youtube.com/@{h}" if h else "https://www.youtube.com"
    elif 'facebook' in plat:
        if clean_author:
            return f"https://www.facebook.com/search/top?q={urllib.parse.quote(clean_author)}"
        return "https://www.facebook.com"
    return "#"

def _render_viral_cards_grid(df, platform_name, title, breadcrumb, page_num=1, page_size=6):
    """
    Renders 6 viral content cards in a responsive 3x2 grid dynamically from df.
    Features:
    - Accurate post-processed sentiment classification (Positive / Neutral / Negative)
    - Clickable profile link (avatar & username) opening in new tab
    - Clickable post snippet & direct 'Buka Postingan ↗' action button opening in new tab
    """
    render_slide_header(title, breadcrumb)
    
    df_plat = df[df['platform'].str.lower().str.contains(platform_name.lower())]
    if df_plat.empty: df_plat = df
    
    # Sort by total engagement descending
    sort_col = 'total_engagement' if 'total_engagement' in df_plat.columns else ('likes' if 'likes' in df_plat.columns else df_plat.columns[0])
    df_sorted = df_plat.sort_values(sort_col, ascending=False)
    
    start_idx = (page_num - 1) * page_size
    df_slice = df_sorted.iloc[start_idx : start_idx + page_size]
    
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    for idx, (_, row) in enumerate(df_slice.iterrows()):
        c = cols[idx % 3]
        
        raw_text = str(row.get('raw_content', row.get('cleaned_content', '')))
        curr_sent = str(row.get('sentiment_name', 'Netral'))
        curr_score = float(row.get('sentiment_score', 0.0))
        
        # Ensure highest precision sentiment classification
        sentiment, _, _, _ = correct_sentiment(raw_text, curr_sent, curr_score)
        
        s_color = '#10B981' if sentiment == 'Positif' else ('#EF4444' if sentiment == 'Negatif' else '#64748B')
        s_bg = '#ECFDF5' if sentiment == 'Positif' else ('#FEF2F2' if sentiment == 'Negatif' else '#F8FAFC')
        
        raw_author = str(row.get('author', 'Anonim')).strip()
        raw_handle = str(row.get('handle', '')).strip()
        clean_name = raw_author.lstrip('@')
        author = f"@{clean_name}"[:25]
        handle = f"@{raw_handle.lstrip('@')}"[:25] if raw_handle else author
        
        # Profile & Post URLs
        profile_url = _get_profile_url(platform_name, author, handle)
        raw_url = str(row.get('url', '')).strip()
        post_url = raw_url if (raw_url and raw_url != 'nan' and raw_url.startswith('http')) else profile_url
        
        clean_snippet = " ".join(raw_text.split())
        if len(clean_snippet) > 160:
            clean_snippet = clean_snippet[:157] + "..."
            
        likes_val = fmt_val(row.get('likes', 0))
        shares_val = fmt_val(max(row.get('shares', 0), row.get('reposts', 0)))
        date_val = str(row.get('date_str', '14 Okt'))
        
        with c:
            render_html(f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:15px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:225px; display:flex; flex-direction:column; justify-content:space-between; transition:all 0.2s ease;">
<div>
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
<a href="{profile_url}" target="_blank" rel="noopener noreferrer" style="display:flex; align-items:center; gap:8px; text-decoration:none; color:inherit;" title="Buka profil {author} di tab baru">
<div style="width:35px; height:35px; border-radius:50%; background:#0F172A; color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; flex-shrink:0;">
{author[:2].upper()}
</div>
<div style="overflow:hidden;">
<div style="font-size:12px; font-weight:700; color:#0F172A; line-height:1.2; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; transition:color 0.15s ease;" onmouseover="this.style.color='#2563EB'" onmouseout="this.style.color='#0F172A'">
{author}
</div>
<div style="font-size:10.5px; color:#64748B; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">
{handle}
</div>
</div>
</a>
<div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
<a href="{post_url}" target="_blank" rel="noopener noreferrer" style="display:inline-flex; align-items:center; text-decoration:none;" title="Buka postingan di {platform_name}">
<span>{get_platform_icon(platform_name, size=15)}</span>
</a>
<span style="font-size:10px; font-weight:700; color:{s_color}; background:{s_bg}; padding:2.5px 8px; border-radius:5px; border:1px solid {s_color}35;">
{sentiment}
</span>
</div>
</div>
<a href="{post_url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; color:inherit; display:block;" title="Klik untuk membuka postingan di tab baru">
<div style="font-size:11.8px; color:#334155; line-height:1.55; margin-bottom:12px; cursor:pointer; transition:color 0.15s ease;" onmouseover="this.style.color='#1D4ED8'" onmouseout="this.style.color='#334155'">
"{clean_snippet}"
</div>
</a>
</div>
<div style="border-top:1px solid #F1F5F9; padding-top:9px; display:flex; justify-content:space-between; align-items:center; font-size:10.5px; color:#64748B;">
<div>
<span style="font-weight:700; color:#0F172A;">{shares_val}</span> Shares &bull; 
<span style="font-weight:700; color:#0F172A;">{likes_val}</span> Likes
</div>
<div style="display:flex; align-items:center; gap:6px;">
<span>{date_val}</span>
<span style="color:#CBD5E1;">&bull;</span>
<a href="{post_url}" target="_blank" rel="noopener noreferrer" style="color:#2563EB; font-weight:700; text-decoration:none; font-size:10.5px; display:inline-flex; align-items:center; gap:3px; padding:2px 6px; border-radius:4px; background:#EFF6FF;" title="Buka tautan postingan asli di tab baru" onmouseover="this.style.background='#DBEAFE'" onmouseout="this.style.background='#EFF6FF'">
Buka ↗
</a>
</div>
</div>
</div>""")
            
    render_slide_footer()


# SLIDES 39 - 42: VIRAL TWITTER (PAGES 1 - 4)
def render_slide_viral_twitter_1(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Twitter", "VIRAL: TWITTER / X (HALAMAN 1)", f"{topic_label} &bull; Cuitan Viral Teratas &bull; {date_str}", page_num=1)

def render_slide_viral_twitter_2(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Twitter", "VIRAL: TWITTER / X (HALAMAN 2)", f"{topic_label} &bull; Cuitan Viral Peringkat 7 - 12 &bull; {date_str}", page_num=2)

def render_slide_viral_twitter_3(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Twitter", "VIRAL: TWITTER / X (HALAMAN 3)", f"{topic_label} &bull; Cuitan Viral Peringkat 13 - 18 &bull; {date_str}", page_num=3)

def render_slide_viral_twitter_4(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Twitter", "VIRAL: TWITTER / X (HALAMAN 4)", f"{topic_label} &bull; Cuitan Viral Peringkat 19 - 24 &bull; {date_str}", page_num=4)


# SLIDE 43: FACEBOOK
def render_slide_viral_facebook(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Facebook", "VIRAL: FACEBOOK", f"{topic_label} &bull; Unggahan Viral Terpopuler &bull; {date_str}", page_num=1)

# SLIDE 44: INSTAGRAM
def render_slide_viral_instagram(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Instagram", "VIRAL: INSTAGRAM", f"{topic_label} &bull; Konten Viral Terpopuler &bull; {date_str}", page_num=1)

# SLIDE 45: YOUTUBE
def render_slide_viral_youtube(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "YouTube", "VIRAL: YOUTUBE", f"{topic_label} &bull; Video Paling Banyak Ditonton &bull; {date_str}", page_num=1)

# SLIDE 46: TIKTOK
def render_slide_viral_tiktok(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "TikTok", "VIRAL: TIKTOK", f"{topic_label} &bull; Video FYP Terpopuler &bull; {date_str}", page_num=1)

# SLIDE 47: THREADS
def render_slide_viral_threads(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    _render_viral_cards_grid(df, "Threads", "VIRAL: THREADS", f"{topic_label} &bull; Utas Paling Banyak Dibagikan &bull; {date_str}", page_num=1)
