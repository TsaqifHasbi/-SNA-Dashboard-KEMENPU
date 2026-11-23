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

        # ======================================================================
        # DRILL-DOWN INTERAKTIF PER TANGGAL & SENTIMEN (POIN 1)
        # ======================================================================
        st.markdown("---")
        st.markdown("#### 🔍 Telusuri Postingan Berdasarkan Tanggal & Sentimen")
        st.caption("Pilih tanggal tertentu pada tren di atas, lalu klik sentimen yang ingin dibedah untuk langsung memunculkan postingan publik terkait.")

        valid_dates = sorted(df_filtered['date_str'].dropna().unique(), reverse=True)
        if valid_dates:
            c_d1, c_d2 = st.columns([1.3, 2.7], vertical_alignment="bottom")
            with c_d1:
                sel_date = st.selectbox(
                    "📅 Pilih Tanggal Analisis:",
                    valid_dates,
                    index=0,
                    key="trend_drill_date"
                )

            df_on_date = df_filtered[df_filtered['date_str'] == sel_date]
            cnt_neg = int((df_on_date['sentiment_name'] == 'Negatif').sum())
            cnt_net = int((df_on_date['sentiment_name'] == 'Netral').sum())
            cnt_pos = int((df_on_date['sentiment_name'] == 'Positif').sum())
            cnt_tot = len(df_on_date)

            sent_choices = [
                f"Semua ({cnt_tot:,})",
                f"🔴 Negatif ({cnt_neg:,})",
                f"⚪ Netral ({cnt_net:,})",
                f"🟢 Positif ({cnt_pos:,})"
            ]

            with c_d2:
                sel_sent_choice = st.radio(
                    "Pilih Filter Sentimen:",
                    sent_choices,
                    index=1 if cnt_neg > 0 else (0 if cnt_tot > 0 else 0),
                    horizontal=True,
                    key=f"trend_drill_sent_{sel_date}"
                )

            if "Negatif" in sel_sent_choice:
                df_show = df_on_date[df_on_date['sentiment_name'] == 'Negatif']
                s_lbl = "Negatif"
                s_theme = "#EF4444"
                s_bg = "#FEF2F2"
            elif "Positif" in sel_sent_choice:
                df_show = df_on_date[df_on_date['sentiment_name'] == 'Positif']
                s_lbl = "Positif"
                s_theme = "#10B981"
                s_bg = "#ECFDF5"
            elif "Netral" in sel_sent_choice:
                df_show = df_on_date[df_on_date['sentiment_name'] == 'Netral']
                s_lbl = "Netral"
                s_theme = "#64748B"
                s_bg = "#F8FAFC"
            else:
                df_show = df_on_date
                s_lbl = "Semua Sentimen"
                s_theme = "#2563EB"
                s_bg = "#EFF6FF"

            st.markdown(f"""
            <div style="background:{s_bg}; border-left:3px solid {s_theme}; padding:7px 12px; border-radius:4px; font-size:11.5px; margin:8px 0 14px 0;">
                <span style="font-weight:700; color:{s_theme};">Hasil Filter Tanggal {sel_date} &bull; {s_lbl}:</span>
                <span style="color:#475569; margin-left:6px;">Ditemukan {len(df_show):,} postingan.</span>
            </div>
            """, unsafe_allow_html=True)

            if df_show.empty:
                st.info(f"Tidak ada postingan dengan sentimen {s_lbl} pada tanggal {sel_date}.")
            else:
                # Tampilkan maksimal 9 postingan teratas berdasarkan engagement
                sort_col = 'total_engagement' if 'total_engagement' in df_show.columns else 'likes'
                top_posts = df_show.sort_values(by=sort_col, ascending=False).head(9)

                cols_grid = st.columns(3)
                for idx, (_, r) in enumerate(top_posts.iterrows()):
                    col_target = cols_grid[idx % 3]
                    with col_target:
                        author = str(r.get('author', 'Anonim')).strip()[:20]
                        platform = str(r.get('platform', 'Web'))
                        txt = str(r.get('raw_content', r.get('cleaned_content', ''))).strip().replace('\n', ' ')
                        snip = (txt[:150] + "...") if len(txt) > 150 else txt
                        sent_name = str(r.get('sentiment_name', 'Netral'))
                        sc = "#10B981" if sent_name == "Positif" else ("#EF4444" if sent_name == "Negatif" else "#64748B")
                        sbg = "#ECFDF5" if sent_name == "Positif" else ("#FEF2F2" if sent_name == "Negatif" else "#F8FAFC")
                        likes = int(r.get('likes', 0) if pd.notna(r.get('likes')) else 0)
                        shares = int(r.get('shares', 0) if pd.notna(r.get('shares')) else 0)
                        url = str(r.get('url', '')).strip()
                        url_btn = f"<a href='{url}' target='_blank' style='color:#2563EB; font-weight:700; text-decoration:none; font-size:10px; background:#EFF6FF; padding:2px 6px; border-radius:4px;'>Buka ↗</a>" if url and url.startswith("http") else ""

                        st.markdown(f"""
                        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; margin-bottom:12px; min-height:190px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                    <div style="font-size:11px; font-weight:700; color:#0F2942;">{author} <span style="color:#94A3B8; font-weight:400; font-size:9.5px;">({platform})</span></div>
                                    <span style="font-size:9.5px; font-weight:800; color:{sc}; background:{sbg}; padding:1.5px 6px; border-radius:4px; border:1px solid {sc}30;">{sent_name}</span>
                                </div>
                                <div style="font-size:11px; color:#334155; line-height:1.45; margin-bottom:8px;">
                                    "{snip}"
                                </div>
                            </div>
                            <div style="border-top:1px solid #F1F5F9; padding-top:6px; display:flex; justify-content:space-between; align-items:center; font-size:9.5px; color:#64748B;">
                                <span>❤️ {likes:,} &bull; 🔁 {shares:,}</span>
                                {url_btn}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    elif trend_type == "Mentions Trend By Channel":
        with st.container(border=True):
            st.plotly_chart(plot_mentions_trend_channel(df_filtered), use_container_width=True)
        st.caption("Penyebaran volume percakapan bertumpuk berdasarkan platform media sosial dan portal berita.")
    else:
        with st.container(border=True):
            st.plotly_chart(plot_mentions_trend_emotion(df_filtered), use_container_width=True)
        st.caption("Dinamika emosi publik (Senang, Sedih, Marah, Takut, Terkejut, Jijik, Netral) dari waktu ke waktu.")
