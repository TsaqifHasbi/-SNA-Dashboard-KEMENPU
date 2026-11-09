# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
from src.components import (
    extract_top_issues,
    plot_crossplatform_diffusion,
    get_top_terms,
    get_top_hashtags,
)

def render_tab_issues(df_filtered):
    st.subheader("🔍 Top Isu & Pola Difusi Lintas Platform (Issue Diffusion)")
    st.caption("Bagaimana narasi berkembang, menguat, dan berpindah antar-kanal media sosial dan berita.")

    iss_col1, iss_col2 = st.columns([1, 1.2])
    with iss_col1:
        st.markdown("##### 📌 Top Isu Paling Banyak Dibahas")
        top_issues_fig = extract_top_issues(df_filtered, top_n=15)
        if top_issues_fig:
            st.plotly_chart(top_issues_fig, use_container_width=True)
            
    with iss_col2:
        st.markdown("##### 🌐 Matriks Difusi Isu Lintas Platform (Diffusion Heatmap)")
        diff_fig = plot_crossplatform_diffusion(df_filtered, top_n=8)
        if diff_fig:
            st.plotly_chart(diff_fig, use_container_width=True)
            st.caption("Angka menunjukkan frekuensi kemunculan kata kunci isu di masing-masing platform.")

    st.markdown("---")
    st.subheader("🏷️ Tagar dan Term Populer Lintas Platform")
    
    term_c1, term_c2 = st.columns(2)
    with term_c1:
        st.markdown("##### 🔤 20 Term / Kata Kunci Populer")
        term_fig, _ = get_top_terms(df_filtered, top_n=15)
        if term_fig:
            st.plotly_chart(term_fig, use_container_width=True)
            
    with term_c2:
        st.markdown("##### #️⃣ 20 Tagar (#Hashtag) Populer")
        hash_fig, _ = get_top_hashtags(df_filtered, top_n=15)
        if hash_fig:
            st.plotly_chart(hash_fig, use_container_width=True)
