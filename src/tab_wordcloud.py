# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd

from src.components import generate_wordcloud_base64

def render_tab_wordcloud(df_filtered):
    st.subheader("☁️ Dual Word Cloud: Analisis Leksikal Frekuensi vs Jangkauan (Reach)")
    st.markdown("""
    Metodologi resmi slide **Kementerian Pekerjaan Umum** (Slide 6):
    * **Buzz of Cloud (Kiri)**: Kosakata yang paling sering diucapkan masyarakat (*Word Count / Frekuensi Percakapan Organik*).
    * **Word of Cloud (Kanan)**: Kosakata yang menyebar paling luas ke jutaan pemirsa (*High Reach / Virality / Efek Influencer*).
    """)

    wc_col1, wc_col2 = st.columns(2)
    with wc_col1:
        st.markdown("#### 🗣️ Awan Term Seluruh Platform (Buzz of Cloud - Frekuensi)")
        b64_f = generate_wordcloud_base64(df_filtered, by='frequency')
        st.markdown(f'<img src="data:image/png;base64,{b64_f}" style="width:100%; border-radius:10px; border:1px solid #1F2937;">', unsafe_allow_html=True)

    with wc_col2:
        st.markdown("#### 🌐 Awan Term Seluruh Platform (Word of Cloud - Reach / Jangkauan)")
        b64_r = generate_wordcloud_base64(df_filtered, by='reach')
        st.markdown(f'<img src="data:image/png;base64,{b64_r}" style="width:100%; border-radius:10px; border:1px solid #1F2937;">', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### #️⃣ Awan Tagar Seluruh Platform (#Hashtag Cloud)")
    b64_h = generate_wordcloud_base64(df_filtered, by='hashtag')
    st.markdown(f'<img src="data:image/png;base64,{b64_h}" style="width:100%; max-height:360px; object-fit:cover; border-radius:10px; border:1px solid #1F2937;">', unsafe_allow_html=True)
