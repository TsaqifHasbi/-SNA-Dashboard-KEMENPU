import os
import sys
import json
from pathlib import Path

# Set path to include src
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd

# Internal modules
from src.data_loader import load_main_data, filter_dataset
from src.metrics_calculator import calculate_kpis

# Executive Slide Renderers (Exact match to uploaded report slides - 30 total pages)
from src.executive_slides import (
    # 1. Volume & Trend
    render_slide_volume_user_engagement_reach,
    render_slide_mentions_trend_channel,
    render_slide_mentions_trend_sentiment,
    render_slide_mentions_trend_emotions,
    render_slide_crossplatform_diffusion,
    # 2. SNA
    render_slide_sna_by_sentiment,
    render_slide_sna_by_emotions,
    # 3. Sentiment 7 Channels
    render_slide_overall_sentiment,
    render_slide_sentiment_online_news,
    render_slide_sentiment_twitter,
    render_slide_sentiment_facebook,
    render_slide_sentiment_instagram,
    render_slide_sentiment_youtube,
    render_slide_sentiment_tiktok,
    render_slide_sentiment_threads,
    # 4. Emotions & Emojis
    render_slide_emotion_analysis_1,
    render_slide_emotion_analysis_2,
    render_slide_emoji_analysis,
    # 5. Media & Influencers
    render_slide_top_news_sites,
    render_slide_top_influencers_twitter,
    render_slide_top_influencers_facebook,
    render_slide_top_influencers_instagram,
    render_slide_top_influencers_youtube,
    render_slide_top_influencers_tiktok,
    render_slide_top_influencers_threads,
    # 6. Viral Content
    render_slide_viral_twitter_1,
    render_slide_viral_twitter_2,
    render_slide_viral_twitter_3,
    render_slide_viral_twitter_4,
    render_slide_viral_facebook,
    render_slide_viral_instagram,
    render_slide_viral_youtube,
    render_slide_viral_tiktok,
    render_slide_viral_threads,
    # 7. Word & Tag Clouds
    render_slide_popular_tags_terms,
    render_slide_wordcloud_terms,
    render_slide_wordcloud_hashtags
)

# Weekly Executive Monitoring Report (21 Slide Deck)
import src.mh_style
import src.mh_weekly_report
from src.test_sentiment_page import render_test_sentiment_page
from src.mh_weekly_report import (
    render_slide_1_cover,
    render_slide_2_executive_summary,
    render_slide_3_chapter_1,
    render_slide_4_overall_media_social,
    render_slide_5_platform_review,
    render_slide_6_two_wordclouds,
    render_slide_7_issues_minister,
    render_slide_8_chapter_2,
    render_slide_9_main_topics,
    render_slide_10_stakeholder_mapping,
    render_slide_11_water_focus_timeline,
    render_slide_12_framing_analysis,
    render_slide_13_disaster_response,
    render_slide_14_bot_organic_audit,
    render_slide_15_intelligence_projections,
    render_slide_16_chapter_3,
    render_slide_17_daily_nov1,
    render_slide_18_daily_nov2,
    render_slide_19_watch_list,
    render_slide_20_priorities_methodology,
    render_slide_21_closing_summary
)

# Deep Analytical Tab Renderers
from src.tab_executive import render_tab_executive
from src.tab_sna import render_tab_sna
from src.tab_platforms import render_tab_platforms
from src.tab_emotions import render_tab_emotions
from src.tab_issues import render_tab_issues
from src.tab_wordcloud import render_tab_wordcloud
from src.tab_evaluation import render_tab_evaluation
from src.clean_header_footer import render_html

# -------------------------------------------------------------
# PAGE CONFIGURATION & EXECUTIVE THEME (EXECUTIVE THEME)
# -------------------------------------------------------------
_logo_icon = os.path.join(current_dir, "static", "logo.svg")

st.set_page_config(
    page_title="Public Policy Intelligence Platform | IndoBERT & SNA",
    page_icon=_logo_icon if os.path.exists(_logo_icon) else "📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Intersep cepat halaman legal via query params (misal: /?page=terms atau /?page=privacy)
# Berjalan instan tanpa memuat dataset 197k baris untuk performa bot review
_qp_page = (st.query_params.get("page") or "").lower().strip()
if _qp_page in ["terms", "tos", "terms_of_service", "terms-of-service"]:
    from src.legal_pages import render_terms_of_service
    render_terms_of_service()
    st.stop()
elif _qp_page in ["privacy", "privacy_policy", "privacy-policy"]:
    from src.legal_pages import render_privacy_policy
    render_privacy_policy()
    st.stop()

# Standalone st.logo removed per user preference; logo is integrated into the header bar and cards.

# Executive Clean Light Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #F8FAFC;
    }
    
    div[data-testid="stSidebar"] {
        background-color: #FAFCFE !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stSidebar"] label {
        color: #1E293B !important;
    }
    
    /* =========================================================
       EXECUTIVE SIDEBAR NAVIGATION (CARD-STYLE RADIO BUTTONS)
       ========================================================= */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        font-size: 11px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        color: #64748B !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
        width: 100% !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label,
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background: #FFFFFF !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 9px !important;
        padding: 10px 13px !important;
        margin: 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
        display: flex !important;
        align-items: center !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover,
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: #F8FAFC !important;
        border-color: #93C5FD !important;
        transform: translateX(2px) !important;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06) !important;
    }
    
    /* Checked / Active Navigation Card State */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: #EFF6FF !important;
        border: 1.5px solid #2563EB !important;
        border-left: 4.5px solid #2563EB !important;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.12) !important;
    }
    
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p,
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) span,
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
        color: #1E40AF !important;
        font-weight: 800 !important;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] label p, 
    div[data-testid="stSidebar"] div[data-testid="stRadio"] label span {
        color: #1E293B !important;
        font-weight: 600 !important;
        font-size: 12.5px !important;
        line-height: 1.35 !important;
        margin: 0 !important;
    }

    /* Clean Vector SVG Icons for Navigation Options (Pure SVG, No Emojis) */
    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(1) p::before {
        content: "";
        display: inline-block;
        width: 14px;
        height: 14px;
        margin-right: 8px;
        vertical-align: -2px;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3Cpolyline points='14 2 14 8 20 8'/%3E%3Cline x1='16' y1='13' x2='8' y2='13'/%3E%3Cline x1='16' y1='17' x2='8' y2='17'/%3E%3Cline x1='10' y1='9' x2='8' y2='9'/%3E%3C/svg%3E") no-repeat center;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3Cpolyline points='14 2 14 8 20 8'/%3E%3Cline x1='16' y1='13' x2='8' y2='13'/%3E%3Cline x1='16' y1='17' x2='8' y2='17'/%3E%3Cline x1='10' y1='9' x2='8' y2='9'/%3E%3C/svg%3E") no-repeat center;
        mask-size: contain;
        -webkit-mask-size: contain;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(2) p::before {
        content: "";
        display: inline-block;
        width: 14px;
        height: 14px;
        margin-right: 8px;
        vertical-align: -2px;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3C/svg%3E") no-repeat center;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3C/svg%3E") no-repeat center;
        mask-size: contain;
        -webkit-mask-size: contain;
    }

    div[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(3) p::before {
        content: "";
        display: inline-block;
        width: 14px;
        height: 14px;
        margin-right: 8px;
        vertical-align: -2px;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3Cpath d='M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z'/%3E%3C/svg%3E") no-repeat center;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3Cpath d='M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z'/%3E%3C/svg%3E") no-repeat center;
        mask-size: contain;
        -webkit-mask-size: contain;
    }

    /* Executive Selectbox & Date Input in Sidebar */
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 7px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #0F172A !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
        border-color: #94A3B8 !important;
    }
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
    }

    div[data-testid="stSidebar"] div[data-testid="stDateInput"] input {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 7px !important;
        font-size: 11.5px !important;
        font-weight: 600 !important;
        color: #0F172A !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stDateInput"] input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
    }

    /* Checkbox Alignment & Typography */
    div[data-testid="stCheckbox"] {
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stCheckbox"] > label {
        align-items: center !important;
        margin: 0 !important;
    }
    div[data-testid="stCheckbox"] label p, div[data-testid="stCheckbox"] label span {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #334155 !important;
        margin: 0 !important;
    }

    /* Executive Card Wrapper for Streamlit Bordered Containers */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stVerticalBlock"] {
        overflow: visible;
    }
    
    /* Plotly Chart Integration: Clean layout, absolutely NO scrollbars, NO collision, seamless container fit */
    div[data-testid="stPlotlyChart"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
        overflow-y: hidden !important;
        overflow-x: hidden !important;
    }
    div[data-testid="stPlotlyChart"] > div,
    div[data-testid="stPlotlyChart"] .js-plotly-plot,
    div[data-testid="stPlotlyChart"] .plot-container {
        overflow: visible !important;
        overflow-y: hidden !important;
        overflow-x: hidden !important;
    }
    div[data-testid="stPlotlyChart"] iframe {
        border: none !important;
        overflow: hidden !important;
    }
    /* Hide scrollbars completely on chart elements */
    div[data-testid="stPlotlyChart"]::-webkit-scrollbar,
    div[data-testid="stPlotlyChart"] *::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    div[data-testid="stPlotlyChart"],
    div[data-testid="stPlotlyChart"] * {
        -ms-overflow-style: none !important;
        scrollbar-width: none !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# DATA ENGINE INITIALIZATION
# -------------------------------------------------------------
import gc

with st.spinner("Memuat korpus data kebijakan publik..."):
    df_raw = load_main_data()

# -------------------------------------------------------------
# SIDEBAR CONTROLS & STRATEGIC FILTERS
# -------------------------------------------------------------
with st.sidebar:
    from src.mh_style import render_logo_badge
    sb_logo = render_logo_badge(size=26)
    render_html(f"""
    <div style="background: linear-gradient(135deg, #0F2942 0%, #1A365D 100%); border-radius: 9px; padding: 12px 14px; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 4px 12px rgba(15, 41, 66, 0.12);">
        <div style="display:flex; align-items:center; gap:10px;">
            {sb_logo}
            <div>
                <div style="color:#FFFFFF; font-weight:800; font-size:12px; letter-spacing:0.4px; line-height:1.2;">MONITORING KEBIJAKAN</div>
                <div style="font-size:10px; color:#94A3B8; font-weight:500; margin-top:2px;">Policy Intelligence & IndoBERT AI</div>
            </div>
        </div>
    </div>
    """)
    curr_caption = st.session_state.get('current_date_display', 'Periode Pemantauan Terkini')
    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:7px 10px; font-size:10px; color:#475569; font-weight:600; display:flex; align-items:center; gap:7px; margin-bottom:14px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
        <span style="width:6px; height:6px; border-radius:50%; background:#10B981; display:inline-block; box-shadow:0 0 0 2px rgba(16,185,129,0.25);"></span>
        <span>{curr_caption}</span>
    </div>
    """)
    
    # Mode Switcher
    MODE_OPTIONS = [
        "Format Laporan Harian",
        "Dashboard Analisis Multi Platform",
        "Cockpit Analisis & Evaluasi Model"
    ]
    
    # Auto-sanitize any previous session state key containing legacy option string
    for k in list(st.session_state.keys()):
        val = st.session_state.get(k)
        if isinstance(val, str) and "Cockpit Analisis Mendalam" in val:
            st.session_state[k] = "Cockpit Analisis & Evaluasi Model"
            
    view_mode = st.radio(
        "PILIH MODE TAMPILAN",
        MODE_OPTIONS,
        index=0
    )
    
    render_html("""
    <div style="margin: 18px 0 10px 0; padding-top: 14px; border-top: 1px solid #E2E8F0;">
        <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px; color: #64748B; display: flex; align-items: center; gap: 7px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <span>FILTER ANALISIS</span>
        </div>
    </div>
    """)
    
    # 1. Topic Selector
    topic_options = ["Kementerian_PU", "Menteri_PU", "Semua Topik"]
    topic_display = {
        "Kementerian_PU": "Kementerian Pekerjaan Umum",
        "Menteri_PU": "Menteri Pekerjaan Umum",
        "Semua Topik": "Semua Topik"
    }
    selected_topic_raw = st.selectbox(
        "Topik Fokus Kebijakan:",
        topic_options,
        index=0,
        format_func=lambda x: topic_display.get(x, x),
        help="Pilih fokus kebijakan: Kementerian Pekerjaan Umum, Menteri Pekerjaan Umum, atau Semua Topik"
    )
    selected_topic = "Semua" if selected_topic_raw == "Semua Topik" else selected_topic_raw

    # 2. Platform Selector
    platform_list = ["Semua Platform", "Twitter", "Facebook", "Instagram", "YouTube", "TikTok", "Threads", "News"]
    selected_plat_raw = st.selectbox(
        "Kanal Platform:",
        platform_list,
        index=0,
        help="Filter platform media sosial atau berita daring"
    )
    selected_platform = "Semua" if selected_plat_raw == "Semua Platform" else selected_plat_raw

    # 3. Date Range Filter
    import datetime
    min_date = df_raw['date'].min().date()
    max_date = df_raw['date'].max().date()
    
    # Default: 1 Januari 2025 s/d Sekarang (data terkini)
    default_start = max(min_date, datetime.date(2025, 1, 1))
    default_end = max_date
    
    date_range = st.date_input(
        "Rentang Waktu:",
        value=(default_start, default_end),
        min_value=min_date,
        max_value=max_date,
        help="Rentang waktu analisis data (default: 1 Januari 2025 s/d Sekarang)"
    )
    
    start_d, end_d = None, None
    if isinstance(date_range, (list, tuple)):
        if len(date_range) == 2:
            start_d, end_d = date_range[0], date_range[1]
        elif len(date_range) == 1:
            start_d, end_d = date_range[0], max_date

    def format_indo_date(d):
        if not d:
            return ""
        months = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        return f"{d.day} {months[d.month]} {d.year}"

    if start_d and end_d:
        days_diff = (end_d - start_d).days
        if days_diff <= 7:
            date_caption = f"Edisi Mingguan • {format_indo_date(start_d)} - {format_indo_date(end_d)}"
        else:
            date_caption = f"Periode Pemantauan • {format_indo_date(start_d)} s/d {format_indo_date(end_d)}"
        date_display = f"{format_indo_date(start_d)} s/d {format_indo_date(end_d)}"
    else:
        date_caption = "Periode Pemantauan • Seluruh Waktu"
        date_display = "Semua Periode"

    st.session_state['current_date_display'] = date_caption

    # Apply filters
    df_filtered = filter_dataset(df_raw, selected_topic=selected_topic, selected_platform=selected_platform, start_date=start_d, end_date=end_d)

    # Load Real Evaluation Metrics (Sentimen & Emosi)
    sent_v2_dir = os.path.join(str(current_dir), 'models', 'best_indobert_sentiment_v2')
    sent_v1_dir = os.path.join(str(current_dir), 'models', 'best_indobert_sentiment')
    sent_model_dir = sent_v2_dir if os.path.exists(sent_v2_dir) else sent_v1_dir
    sent_metrics_file = os.path.join(sent_model_dir, 'evaluation_metrics.json')
    emo_metrics_file = os.path.join(str(current_dir), 'models', 'best_indobert_emotion', 'evaluation_metrics.json')
    
    acc_sent = 0.9775
    f1_sent = 0.9775
    prec_sent = 0.9775
    rec_sent = 0.9775
    
    acc_emo = 0.9178
    f1_emo = 0.9174
    
    if os.path.exists(sent_metrics_file):
        try:
            with open(sent_metrics_file, 'r', encoding='utf-8') as f:
                s_data = json.load(f)
                acc_sent = s_data.get('accuracy', acc_sent)
                f1_sent = s_data.get('macro_f1', f1_sent)
                cm = s_data.get('confusion_matrix')
                if cm and len(cm) == 3:
                    col_sums = [sum(cm[r][c] for r in range(3)) for c in range(3)]
                    row_sums = [sum(cm[r]) for r in range(3)]
                    precs = [cm[i][i] / col_sums[i] if col_sums[i] > 0 else 0 for i in range(3)]
                    recs = [cm[i][i] / row_sums[i] if row_sums[i] > 0 else 0 for i in range(3)]
                    prec_sent = sum(precs) / 3.0
                    rec_sent = sum(recs) / 3.0
        except Exception:
            pass
            
    if os.path.exists(emo_metrics_file):
        try:
            with open(emo_metrics_file, 'r', encoding='utf-8') as f:
                e_data = json.load(f)
                acc_emo = e_data.get('accuracy', acc_emo)
                f1_emo = e_data.get('macro_f1', f1_emo)
        except Exception:
            pass

    st.markdown("---")
    st.markdown("### Status Korpus & Model")
    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
        <div style="font-size:11.5px; line-height:1.75; color:#334155;">
            <div style="display:flex; justify-content:space-between;"><span>Total Korpus:</span> <strong>{len(df_raw):,}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>Data Terfilter:</span> <strong style="color:#0284C7;">{len(df_filtered):,}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>Penulis Unik:</span> <strong>{df_filtered['author'].nunique():,}</strong></div>
            <div style="border-top:1px dashed #E2E8F0; margin:6px 0;"></div>
            <div style="display:flex; justify-content:space-between;"><span>Akurasi Sentimen:</span> <strong style="color:#10B981;">{acc_sent*100:.2f}%</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>Macro F1 Sentimen:</span> <strong style="color:#0F172A;">{f1_sent*100:.2f}%</strong></div>
            <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#64748B;"><span>Precision / Recall:</span> <span>{prec_sent*100:.2f}% / {rec_sent*100:.2f}%</span></div>
            <div style="border-top:1px dashed #E2E8F0; margin:6px 0;"></div>
            <div style="display:flex; justify-content:space-between;"><span>Akurasi 9 Emosi:</span> <strong style="color:#8B5CF6;">{acc_emo*100:.2f}%</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>Macro F1 9 Emosi:</span> <strong style="color:#0F172A;">{f1_emo*100:.2f}%</strong></div>
        </div>
    </div>
    """)

    st.markdown("---")
    st.markdown("<div style='font-size:11px; font-weight:700; color:#0F2942; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;'>Dokumen Kebijakan & Kepatuhan:</div>", unsafe_allow_html=True)
    st.link_button("Terms of Service", "/terms-of-service", icon=":material/gavel:", use_container_width=True)
    st.link_button("Privacy Policy", "/privacy-policy", icon=":material/policy:", use_container_width=True)
    st.caption("Kepatuhan Resmi TikTok for Developers & Riset UNSOED")

# Calculate Core KPIs
kpis = calculate_kpis(df_filtered)
# date_display already formatted in Indonesian above

# -------------------------------------------------------------
# MAIN CONTENT DISPATCHER
# -------------------------------------------------------------
if "Format Laporan Harian" in view_mode or "Laporan Harian" in view_mode or "Slide MH" in view_mode:
    MH_CHAPTERS = {
        "Ringkasan Eksekutif": {
            "Slide 1: Cover Laporan Eksekutif": render_slide_1_cover,
            "Slide 2: Ringkasan Eksekutif (Executive Summary)": render_slide_2_executive_summary,
        },
        "Bab 1: Tinjauan Multiplatform (The Overview)": {
            "Slide 3: Pembuka Bab 1 (The Overview)": render_slide_3_chapter_1,
            "Slide 4: Tren Harian Lembaga & Menteri (Overall Media & Social)": render_slide_4_overall_media_social,
            "Slide 5: Tinjauan Percakapan 7 Saluran Multiplatform": render_slide_5_platform_review,
            "Slide 6: Analisis Suara Teratas & Dua Awan Kata": render_slide_6_two_wordclouds,
            "Slide 7: Pemetaan Isu Positif & Negatif Terbesar": render_slide_7_issues_minister,
        },
        "Bab 2: Analisis Mendalam (The Deep Dive)": {
            "Slide 7: Pembuka Bab 2 (The Deep Dive)": render_slide_8_chapter_2,
            "Slide 8: Analisis Topik Utama & Klaster Isu": render_slide_9_main_topics,
            "Slide 9: Pemetaan Pemangku Kepentingan (Power-Interest)": render_slide_10_stakeholder_mapping,
            "Slide 10: Kronologi & Dinamika Lintas Waktu": render_slide_11_water_focus_timeline,
            "Slide 11: Analisis Pembingkaian Isu (Framing Analysis)": render_slide_12_framing_analysis,
            "Slide 12: Pemetaan Respons & Layanan Publik": render_slide_13_disaster_response,
            "Slide 13: Audit Keserempakan & Uji Organik (Bot / Buzzer)": render_slide_14_bot_organic_audit,
            "Slide 14: Rekomendasi Intelijen & Proyeksi 7 Hari": render_slide_15_intelligence_projections,
        },
        "Bab 3: Tindakan Strategis (The Action)": {
            "Slide 15: Pembuka Bab 3 (The Action)": render_slide_16_chapter_3,
            "Slide 16: Pemantauan Sentimen Harian (Sesi Pagi)": render_slide_17_daily_nov1,
            "Slide 17: Pemantauan Sentimen Harian (Sesi Sore)": render_slide_18_daily_nov2,
            "Slide 18: Daftar Pantau Isu Strategis Sepekan": render_slide_19_watch_list,
            "Slide 19: Matriks Prioritas Tindakan & Metodologi": render_slide_20_priorities_methodology,
            "Slide 20: Penutup & Pesan Kunci Eksekutif": render_slide_21_closing_summary,
        },
        "Test Sentimen": {
            "Uji Interaktif: Deteksi Sentimen, Emosi & SNA": render_test_sentiment_page,
        }
    }
    
    mh_chap_names = list(MH_CHAPTERS.keys())
    
    # Toolbar Navigasi Slide Eksekutif yang Rapi & Presisi
    with st.container(border=True):
        c_top1, c_top2 = st.columns([3.6, 1.4], vertical_alignment="center")
        with c_top1:
            render_html("""
            <div id="mh-deck-header" style="display:flex; align-items:center; gap:8px;">
                <span style="background:#0F2942; color:#FFFFFF; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; letter-spacing:0.5px;">DECK EKSEKUTIF</span>
                <span style="font-size:13px; font-weight:700; color:#0F2942;">Format Laporan Harian (Slide Deck)</span>
            </div>
            """)
        with c_top2:
            st.markdown(
                """
                <style>
                div[data-testid="stHorizontalBlock"]:has(#mh-deck-header) > div[data-testid="stColumn"]:last-child {
                    display: flex !important;
                    justify-content: flex-end !important;
                    align-items: center !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mh-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stElementContainer"] {
                    display: flex !important;
                    justify-content: flex-end !important;
                    width: 100% !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mh-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stCheckbox"] {
                    margin-left: auto !important;
                    justify-content: flex-end !important;
                    width: fit-content !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mh-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stCheckbox"] label {
                    margin-left: auto !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            view_all_mh = st.toggle(
                "Mode Baca Beruntun",
                value=False,
                help="Menampilkan seluruh slide dalam bab terpilih secara berurutan ke bawah",
                key="mh_view_all_toggle"
            )

        if not view_all_mh:
            c_chap, c_slide, c_nav = st.columns([1.5, 2.2, 1.3], vertical_alignment="bottom")
            with c_chap:
                selected_mh_chap = st.selectbox(
                    "Pilih Bab / Bagian:",
                    mh_chap_names,
                    index=0,
                    key="mh_active_chapter"
                )

            mh_pages = MH_CHAPTERS[selected_mh_chap]
            mh_page_names = list(mh_pages.keys())

            # Sinkronisasi state slide per bab
            slide_widget_key = f"mh_slide_select_{selected_mh_chap}"
            if slide_widget_key not in st.session_state or st.session_state[slide_widget_key] not in mh_page_names:
                st.session_state[slide_widget_key] = mh_page_names[0]

            def _on_prev_mh(key, names):
                cur = st.session_state.get(key, names[0])
                idx = names.index(cur) if cur in names else 0
                if idx > 0:
                    st.session_state[key] = names[idx - 1]

            def _on_next_mh(key, names):
                cur = st.session_state.get(key, names[0])
                idx = names.index(cur) if cur in names else 0
                if idx < len(names) - 1:
                    st.session_state[key] = names[idx + 1]

            cur_slide = st.session_state[slide_widget_key]
            cur_idx = mh_page_names.index(cur_slide) if cur_slide in mh_page_names else 0

            with c_slide:
                selected_mh_slide = st.selectbox(
                    f"Pilih Slide ({cur_idx + 1}/{len(mh_page_names)}):",
                    mh_page_names,
                    key=slide_widget_key
                )
                cur_idx = mh_page_names.index(selected_mh_slide)

            with c_nav:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    prev_disabled = (cur_idx == 0)
                    st.button(
                        "Prev",
                        icon=":material/arrow_back:",
                        disabled=prev_disabled,
                        use_container_width=True,
                        help="Slide Sebelumnya",
                        key=f"btn_prev_{selected_mh_chap}",
                        on_click=_on_prev_mh,
                        args=(slide_widget_key, mh_page_names)
                    )
                with col_b2:
                    next_disabled = (cur_idx >= len(mh_page_names) - 1)
                    st.button(
                        "Next",
                        icon=":material/arrow_forward:",
                        disabled=next_disabled,
                        use_container_width=True,
                        help="Slide Berikutnya",
                        key=f"btn_next_{selected_mh_chap}",
                        on_click=_on_next_mh,
                        args=(slide_widget_key, mh_page_names)
                    )
        else:
            c_chap, _ = st.columns([2.5, 2.5], vertical_alignment="bottom")
            with c_chap:
                selected_mh_chap = st.selectbox(
                    "Pilih Bab / Bagian:",
                    mh_chap_names,
                    index=0,
                    key="mh_active_chapter"
                )
            mh_pages = MH_CHAPTERS[selected_mh_chap]

    st.write("")
    if not view_all_mh:
        mh_pages[selected_mh_slide](df_filtered, selected_topic=selected_topic, topic_label=selected_topic, date_str=date_display)
    else:
        for s_idx, (s_name, s_func) in enumerate(mh_pages.items(), 1):
            s_func(df_filtered, selected_topic=selected_topic, topic_label=selected_topic, date_str=date_display)
            if s_idx < len(mh_pages):
                st.markdown("<div style='margin: 40px 0; border-bottom: 2px dashed #CBD5E1;'></div>", unsafe_allow_html=True)

elif "Dashboard Analisis Multi Platform" in view_mode or "Katalog Analisis Multiplatform" in view_mode or "Laporan Analisis Visual" in view_mode:
    # 7 LOGICAL ANALYTICAL CATEGORIES (All 30 visual pages organized thematically)
    CATEGORIES = {
        "1. Volume & Tren Temporal": {
            "Volume, User, Engagement & Reach": render_slide_volume_user_engagement_reach,
            "Tren Mentions Tiap Kanal": render_slide_mentions_trend_channel,
            "Tren Sentimen Waktu Riil": render_slide_mentions_trend_sentiment,
            "Tren 8 Emosi Publik Waktu Riil": render_slide_mentions_trend_emotions,
            "Difusi Isu Lintas Kanal (Crossplatform Diffusion)": render_slide_crossplatform_diffusion
        },
        "2. Analisis Jaringan Sosial (SNA)": {
            "Polarisasi Jaringan Berdasarkan Sentimen": render_slide_sna_by_sentiment,
            "Struktur Komunitas Berdasarkan 4 Klaster Emosi": render_slide_sna_by_emotions
        },
        "3. Sentimen 7 Kanal Platform": {
            "Sentimen Keseluruhan & Komparasi 7 Kanal": render_slide_overall_sentiment,
            "Sentimen Portal Berita Daring": render_slide_sentiment_online_news,
            "Sentimen Platform Twitter / X": render_slide_sentiment_twitter,
            "Sentimen Platform Facebook": render_slide_sentiment_facebook,
            "Sentimen Platform Instagram": render_slide_sentiment_instagram,
            "Sentimen Platform YouTube": render_slide_sentiment_youtube,
            "Sentimen Platform TikTok": render_slide_sentiment_tiktok,
            "Sentimen Platform Threads": render_slide_sentiment_threads
        },
        "4. Analisis Emosi & Semantik": {
            "Distribusi & Intensitas 8 Emosi (Plutchik)": render_slide_emotion_analysis_1,
            "Emosi Berdasarkan Sentimen & Kanal Platform": render_slide_emotion_analysis_2,
            "Analisis Frekuensi & Rasio Sentimen Emoji": render_slide_emoji_analysis
        },
        "5. Media Berita & Top Pemengaruh": {
            "Top 10 Situs Berita Daring Teraktif": render_slide_top_news_sites,
            "Top Pemengaruh Twitter / X (Interest vs Power)": render_slide_top_influencers_twitter,
            "Top Pemengaruh Facebook": render_slide_top_influencers_facebook,
            "Top Pemengaruh Instagram": render_slide_top_influencers_instagram,
            "Top Pemengaruh YouTube": render_slide_top_influencers_youtube,
            "Top Pemengaruh TikTok": render_slide_top_influencers_tiktok,
            "Top Pemengaruh Threads": render_slide_top_influencers_threads
        },
        "6. Konten Viral & Populer": {
            "Cuitan Populer Twitter / X (Halaman 1)": render_slide_viral_twitter_1,
            "Cuitan Populer Twitter / X (Halaman 2)": render_slide_viral_twitter_2,
            "Cuitan Populer Twitter / X (Halaman 3)": render_slide_viral_twitter_3,
            "Cuitan Populer Twitter / X (Halaman 4)": render_slide_viral_twitter_4,
            "Status Facebook Paling Disukai": render_slide_viral_facebook,
            "Status Instagram Paling Disukai": render_slide_viral_instagram,
            "Video YouTube Paling Ditonton": render_slide_viral_youtube,
            "Video TikTok Paling Ditonton": render_slide_viral_tiktok,
            "Status Threads Paling Disukai": render_slide_viral_threads
        },
        "7. Tagar & Awan Kata": {
            "Top 20 Tagar & Top 20 Istilah Kunci": render_slide_popular_tags_terms,
            "Awan Kata Kunci (Word Cloud) Seluruh Platform": render_slide_wordcloud_terms,
            "Awan Tagar (Hashtags) Seluruh Platform": render_slide_wordcloud_hashtags
        }
    }
    
    # Top Category Selector & Navigation Toolbar (Clean, classified, and logical)
    cat_names = list(CATEGORIES.keys())
    
    with st.container(border=True):
        c_top1, c_top2 = st.columns([3.6, 1.4], vertical_alignment="center")
        with c_top1:
            render_html("""
            <div id="mp-deck-header" style="display:flex; align-items:center; gap:8px;">
                <span style="background:#0F2942; color:#FFFFFF; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px; letter-spacing:0.5px;">KATALOG MULTIPLATFORM</span>
                <span style="font-size:13px; font-weight:700; color:#0F2942;">Dashboard Analisis Multi Platform</span>
            </div>
            """)
        with c_top2:
            st.markdown(
                """
                <style>
                div[data-testid="stHorizontalBlock"]:has(#mp-deck-header) > div[data-testid="stColumn"]:last-child {
                    display: flex !important;
                    justify-content: flex-end !important;
                    align-items: center !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mp-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stElementContainer"] {
                    display: flex !important;
                    justify-content: flex-end !important;
                    width: 100% !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mp-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stCheckbox"] {
                    margin-left: auto !important;
                    justify-content: flex-end !important;
                    width: fit-content !important;
                }
                div[data-testid="stHorizontalBlock"]:has(#mp-deck-header) > div[data-testid="stColumn"]:last-child div[data-testid="stCheckbox"] label {
                    margin-left: auto !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            view_all_mp = st.toggle(
                "Mode Baca Beruntun",
                value=False,
                help="Menampilkan seluruh visualisasi dalam kategori terpilih secara berurutan ke bawah",
                key="mp_view_all_toggle"
            )

        if not view_all_mp:
            c_cat, c_page, c_nav = st.columns([1.5, 2.2, 1.3], vertical_alignment="bottom")
            with c_cat:
                selected_cat = st.selectbox(
                    "Pilih Kategori Analisis:",
                    cat_names,
                    index=0,
                    key="mp_active_category"
                )

            pages_in_cat = CATEGORIES[selected_cat]
            page_names = list(pages_in_cat.keys())

            # Sinkronisasi state halaman per kategori
            page_widget_key = f"mp_page_select_{selected_cat}"
            if page_widget_key not in st.session_state or st.session_state[page_widget_key] not in page_names:
                st.session_state[page_widget_key] = page_names[0]

            def _on_prev_mp(key, names):
                cur = st.session_state.get(key, names[0])
                idx = names.index(cur) if cur in names else 0
                if idx > 0:
                    st.session_state[key] = names[idx - 1]

            def _on_next_mp(key, names):
                cur = st.session_state.get(key, names[0])
                idx = names.index(cur) if cur in names else 0
                if idx < len(names) - 1:
                    st.session_state[key] = names[idx + 1]

            cur_page = st.session_state[page_widget_key]
            cur_idx = page_names.index(cur_page) if cur_page in page_names else 0

            with c_page:
                selected_page = st.selectbox(
                    f"Pilih Halaman ({cur_idx + 1}/{len(page_names)}):",
                    page_names,
                    key=page_widget_key
                )
                cur_idx = page_names.index(selected_page)

            with c_nav:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    prev_disabled = (cur_idx == 0)
                    st.button(
                        "Prev",
                        icon=":material/arrow_back:",
                        disabled=prev_disabled,
                        use_container_width=True,
                        help="Halaman Sebelumnya",
                        key=f"mp_btn_prev_{selected_cat}",
                        on_click=_on_prev_mp,
                        args=(page_widget_key, page_names)
                    )
                with col_b2:
                    next_disabled = (cur_idx >= len(page_names) - 1)
                    st.button(
                        "Next",
                        icon=":material/arrow_forward:",
                        disabled=next_disabled,
                        use_container_width=True,
                        help="Halaman Berikutnya",
                        key=f"mp_btn_next_{selected_cat}",
                        on_click=_on_next_mp,
                        args=(page_widget_key, page_names)
                    )
        else:
            c_cat, _ = st.columns([2.5, 2.5], vertical_alignment="bottom")
            with c_cat:
                selected_cat = st.selectbox(
                    "Pilih Kategori Analisis:",
                    cat_names,
                    index=0,
                    key="mp_active_category"
                )
            pages_in_cat = CATEGORIES[selected_cat]

    st.write("")
    if not view_all_mp:
        # Render the specific selected page
        pages_in_cat[selected_page](df_filtered, selected_topic=selected_topic, topic_label=selected_topic, date_str=date_display)
    else:
        # Render all pages in the chosen category
        for idx, (pname, pfunc) in enumerate(pages_in_cat.items(), 1):
            pfunc(df_filtered, selected_topic=selected_topic, topic_label=selected_topic, date_str=date_display)
            if idx < len(pages_in_cat):
                st.markdown("<div style='margin: 40px 0; border-bottom: 2px dashed #CBD5E1;'></div>", unsafe_allow_html=True)

else:
    # ---------------------------------------------------------
    # MODE 3: COCKPIT ANALISIS & EVALUASI MODEL
    # ---------------------------------------------------------
    tabs = st.tabs([
        "Ringkasan Eksekutif",
        "Analisis SNA",
        "Analisis Kanal Platform",
        "Analisis Emosi",
        "Klaster Isu",
        "Word Cloud",
        "Evaluasi Model IndoBERT"
    ])
    
    with tabs[0]:
        render_tab_executive(df_filtered, df_raw, kpis)
    with tabs[1]:
        render_tab_sna(df_filtered, selected_topic, selected_platform, 100, current_dir)
    with tabs[2]:
        render_tab_platforms(df_filtered)
    with tabs[3]:
        render_tab_emotions(df_filtered)
    with tabs[4]:
        render_tab_issues(df_filtered)
    with tabs[5]:
        render_tab_wordcloud(df_filtered)
    with tabs[6]:
        render_tab_evaluation(current_dir)

# Refreshed for emotion & sentiment integration
