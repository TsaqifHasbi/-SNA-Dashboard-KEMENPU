# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
from src.metrics_calculator import calculate_z_test, calculate_framing_entman
from src.components import (
    plot_sentiment_donut,
    plot_mentions_trend_sentiment,
    plot_mentions_trend_channel,
    plot_mentions_trend_emotion,
)

def render_tab_executive(df_filtered, df_raw, kpis):
    st.subheader("📊 Indikator Sentimen Keseluruhan & Evaluasi Signifikansi Statistik")
    
    col_donut, col_nss_stat = st.columns([1, 1.4])
    
    with col_donut:
        st.markdown("##### 🍩 Distribusi Sentimen IndoBERT & NSS")
        st.plotly_chart(plot_sentiment_donut(df_filtered, kpis['nss']), use_container_width=True)
        st.caption(f"Positif: **{kpis['pos_pct']}%** ({kpis['positive']:,}) | Netral: **{kpis['net_pct']}%** ({kpis['neutral']:,}) | Negatif: **{kpis['neg_pct']}%** ({kpis['negative']:,})")

    with col_nss_stat:
        st.markdown("##### 📐 Metrik Pemantauan Standar Kementerian PU & Media & Policy Intelligence")
        
        z_score, p_val, z_status = calculate_z_test(
            kpis['positive'], kpis['volume'],
            df_raw['sentiment_name'].value_counts().get('Positif', 0), len(df_raw)
        )
        
        nss_badge = f"<span class='badge-pos'>POSITIF KUAT (+{kpis['nss']})</span>" if kpis['nss'] > 10 else (
            f"<span class='badge-neg'>KRITIS (-{abs(kpis['nss'])})</span>" if kpis['nss'] < -10 else f"<span class='badge-net'>STABIL / NETRAL ({kpis['nss']})</span>"
        )
        
        stat_badge = f"<span class='badge-pos'>SIGNIFIKAN ({z_status})</span>" if z_status == "NYATA" else f"<span class='badge-net'>DERAU RANDOM ({z_status})</span>"
        
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; align-items:center;">
                <span style="font-size:14px; color:#475569; font-weight:600;">Status Net Sentiment Score (NSS):</span>
                {nss_badge}
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; align-items:center;">
                <span style="font-size:14px; color:#475569; font-weight:600;">Uji Dua Sampel Proporsi (Z-Test):</span>
                {stat_badge}
            </div>
            <div style="font-size:12.5px; color:#64748B; line-height:1.6; border-top:1px solid #F1F5F9; padding-top:10px;">
                • <b>Z-Score:</b> <code>{z_score}</code> (Ambang batas |Z| >= 1.96 taraf nyata 95%)<br>
                • <b>P-Value:</b> <code>{p_val}</code><br>
                • <b>Interpretasi Kebijakan:</b> {'Perubahan opini publik terhadap isu ini nyata secara statistik, bukan sekadar fluktuasi derau sesaat. Diperlukan respons strategi komunikasi.' if z_status == 'NYATA' else 'Perubahan sentimen masih dalam ambang derau statistik acak. Pantau pergerakan narasi tanpa perlu kepanikan reaktif.'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        framing = calculate_framing_entman(df_filtered)
        if framing:
            st.markdown("##### 🎯 Analisis 4 Fungsi Framing Entman & Edelman")
            f1, f2 = st.columns(2)
            with f1:
                st.markdown(f"**1. Definisi Masalah:** {framing['problem_definition']['percent']}% ({framing['problem_definition']['count']:,} teks)")
                st.markdown(f"**2. Penyebab:** {framing['causal_interpretation']['percent']}% ({framing['causal_interpretation']['count']:,} teks)")
            with f2:
                st.markdown(f"**3. Evaluasi Moral:** {framing['moral_evaluation']['percent']}% ({framing['moral_evaluation']['count']:,} teks)")
                st.markdown(f"**4. Rekomendasi:** {framing['treatment_recommendation']['percent']}% ({framing['treatment_recommendation']['count']:,} teks)")

    st.markdown("---")
    st.subheader("📈 Tren Percakapan Lintas Waktu (Mentions Trend)")
    trend_type = st.radio(
        "Pilih Dimensi Analisis Tren:",
        ["Mentions Trend By Sentimen (+ 7-Day Moving Average)", "Mentions Trend By Channel", "Mentions Trend By Emotions"],
        horizontal=True
    )
    
    if trend_type == "Mentions Trend By Sentimen (+ 7-Day Moving Average)":
        with st.container(border=True):
            st.plotly_chart(plot_mentions_trend_sentiment(df_filtered), use_container_width=True)
        st.caption("Garis biru menunjukkan Rerata Bergerak 7 Hari (7-Day Moving Average) untuk meredam noise harian.")
    elif trend_type == "Mentions Trend By Channel":
        with st.container(border=True):
            st.plotly_chart(plot_mentions_trend_channel(df_filtered), use_container_width=True)
        st.caption("Penyebaran volume percakapan bertumpuk berdasarkan platform media sosial dan portal berita.")
    else:
        with st.container(border=True):
            st.plotly_chart(plot_mentions_trend_emotion(df_filtered), use_container_width=True)
        st.caption("Dinamika emosi publik (Senang, Sedih, Marah, Takut, Terkejut, Jijik, Netral) dari waktu ke waktu.")
