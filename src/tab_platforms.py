# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
from src.components import (
    plot_platform_sentiment_bars,
    plot_platform_sentiment_donut,
    plot_sentiment_timeline_platform,
    plot_top_influencers,
    get_top_posts,
    get_top_news_sites,
)

def render_tab_platforms(df_filtered):
    st.subheader("📱 Performa Opini & Pemengaruh pada 7 Kanal Media Sosial dan Berita")
    st.caption("Analisis komparatif di Twitter/X, Facebook, Instagram, YouTube, TikTok, Threads, dan Berita Daring.")
    
    st.plotly_chart(plot_platform_sentiment_bars(df_filtered), use_container_width=True)
    
    st.markdown("---")
    
    plat_tab_names = [
        "Twitter / X", "Facebook", "Instagram",
        "YouTube", "TikTok", "Threads", "Online News"
    ]
    plat_keys = ["Twitter", "Facebook", "Instagram", "YouTube", "TikTok", "Threads", "News"]
    
    p_tabs = st.tabs(plat_tab_names)
    
    for p_tab, p_key in zip(p_tabs, plat_keys):
        with p_tab:
            p_sub = df_filtered[df_filtered['platform'] == p_key]
            if len(p_sub) == 0:
                st.info(f"Belum ada data untuk platform {p_key} pada filter yang dipilih.")
                continue
                
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.markdown(f"##### 🍩 Sentimen di {p_key}")
                st.plotly_chart(plot_platform_sentiment_donut(df_filtered, p_key), use_container_width=True)
                
            with pc2:
                st.markdown(f"##### 📈 Tren Waktu Sentimen di {p_key}")
                st.plotly_chart(plot_sentiment_timeline_platform(df_filtered, p_key), use_container_width=True)
                
            st.markdown("---")
            
            pi_col1, pi_col2 = st.columns([1.1, 1.3])
            
            with pi_col1:
                st.markdown(f"##### 👑 Top Pemengaruh di {p_key}")
                st.plotly_chart(plot_top_influencers(df_filtered, p_key, top_n=8), use_container_width=True)
                
            with pi_col2:
                if p_key == "Twitter":
                    st.markdown("##### 🔁 Unggahan X Paling Banyak Dibagi (Most Reposted)")
                elif p_key == "Facebook":
                    st.markdown("##### 👍 Status Facebook Paling Banyak Disukai (Most Liked)")
                elif p_key == "Instagram":
                    st.markdown("##### ❤️ Status Instagram Paling Banyak Disukai (Most Liked)")
                elif p_key == "YouTube":
                    st.markdown("##### 👁️ Video YouTube Paling Banyak Ditonton (Most Viewed)")
                elif p_key == "TikTok":
                    st.markdown("##### 👁️ Video TikTok Paling Banyak Ditonton (Most Viewed)")
                elif p_key == "Threads":
                    st.markdown("##### 💬 Status Threads Paling Banyak Disukai (Most Liked)")
                else:
                    st.markdown("##### 📰 Berita dengan Total Interaksi Tertinggi")

                top_posts = get_top_posts(df_filtered, p_key, top_n=5)
                for _, r in top_posts.iterrows():
                    badge_cls = "badge-pos" if r['sentiment_name'] == 'Positif' else ("badge-neg" if r['sentiment_name'] == 'Negatif' else "badge-net")
                    st.markdown(f"""
                    <div class="post-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-weight:700; color:#38BDF8;">@{str(r['author']).strip().lstrip('@')}</span>
                            <span class="{badge_cls}">{r['sentiment_name']}</span>
                        </div>
                        <div style="color:#E2E8F0; font-size:13px; line-height:1.5; margin-bottom:10px;">
                            "{r['cleaned_content'][:240]}..."
                        </div>
                        <div style="font-size:11.5px; color:#94A3B8; display:flex; gap:16px;">
                            <span>❤️ {r['likes']:,} Likes</span>
                            <span>💬 {r['comments']:,} Komentar</span>
                            <span>🔁 {r['shares'] + r['reposts']:,} Share</span>
                            <span>👁️ {r['views']:,} Views</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if p_key == "News":
                st.markdown("---")
                st.markdown("##### 🌐 Situs Berita Paling Banyak Memberitakan (Media Share of Voice)")
                news_fig = get_top_news_sites(df_filtered, top_n=12)
                if news_fig:
                    st.plotly_chart(news_fig, use_container_width=True)
