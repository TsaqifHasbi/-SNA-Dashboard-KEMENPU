import os
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore[missing-import]
import streamlit.components.v1 as components_v1
from src.sna_engine import build_sna_network, generate_pyvis_html, export_gephi_gexf, get_network_metrics

def render_tab_sna(df_filtered, selected_topic, selected_platform, sna_max_nodes, current_dir):
    st.subheader("🌐 Social Network Analysis (SNA) Interaktif")
    st.markdown("""
    Visualisasi graf interaktif jejaring komunikasi dan difusi opini publik:
    - **Node (Titik)**: Akun pengunggah atau akun yang dirujuk/di-mention.
    - **Edge (Garis)**: Interaksi pengutipan/penyebutan (*mention*) antara dua akun.
    - **Ukuran Node**: Berbanding lurus dengan nilai *In-Degree Centrality* (semakin besar, semakin sering dirujuk/berpengaruh).
    """)

    col_sna_ctrl1, col_sna_ctrl2, col_sna_ctrl3 = st.columns(3)
    with col_sna_ctrl1:
        sna_dimension = st.selectbox(
            "Pilih Mode Pewarnaan Graf SNA:",
            ["SNA By Sentiment", "SNA By Emotions"],
            help="SNA By Sentiment mewarnai node berdasarkan Positif/Netral/Negatif. SNA By Emotions mewarnai node berdasarkan 7 emosi dasar."
        )
    with col_sna_ctrl2:
        sna_topic_choice = st.selectbox(
            "Fokus Topik SNA:",
            ["Topik Terpilih Saat Ini", "Kementerian_PU", "Menteri_PU", "Semua Topik"]
        )
    with col_sna_ctrl3:
        sna_platform_choice = st.selectbox(
            "Fokus Platform SNA:",
            ["Platform Terpilih Saat Ini", "Twitter", "Facebook", "Instagram", "YouTube", "TikTok", "Threads", "News", "Semua Platform"]
        )

    target_topic = selected_topic if sna_topic_choice == "Topik Terpilih Saat Ini" else ("Semua" if sna_topic_choice == "Semua Topik" else sna_topic_choice)
    target_plat = selected_platform if sna_platform_choice == "Platform Terpilih Saat Ini" else ("Semua" if sna_platform_choice == "Semua Platform" else sna_platform_choice)
    sna_mode = "emotion" if sna_dimension == "SNA By Emotions" else "sentiment"

    with st.spinner("Membangun struktur topologi graf SNA..."):
        G = build_sna_network(
            df_filtered,
            max_nodes=sna_max_nodes,
            topic_filter=target_topic,
            platform_filter=target_plat,
            mode=sna_mode
        )
        net_metrics = get_network_metrics(G)

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total Node (Aktor)", f"{net_metrics['nodes']:,}")
    m_col2.metric("Total Edge (Relasi)", f"{net_metrics['edges']:,}")
    m_col3.metric("Kerapatan Jaringan (Density)", f"{net_metrics['density']:.5f}")
    m_col4.metric("Rerata Derajat (Avg Degree)", f"{net_metrics['avg_degree']}")

    if sna_mode == "emotion":
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; padding:8px 14px; border-radius:8px; margin-bottom:12px; font-size:12px; display:flex; gap:14px; flex-wrap:wrap; color:#334155;">
            <span><b style="color:#10B981;">●</b> Joy</span>
            <span><b style="color:#06B6D4;">●</b> Percaya</span>
            <span><b style="color:#F59E0B;">●</b> Antisipasi</span>
            <span><b style="color:#EF4444;">●</b> Marah</span>
            <span><b style="color:#8B5CF6;">●</b> Takut</span>
            <span><b style="color:#84CC16;">●</b> Jijik</span>
            <span><b style="color:#3B82F6;">●</b> Sedih</span>
            <span><b style="color:#A78BFA;">●</b> Surprise</span>
            <span><b style="color:#64748B;">●</b> Informatif</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; padding:8px 14px; border-radius:8px; margin-bottom:12px; font-size:12px; display:flex; gap:20px; color:#334155;">
            <span><b style="color:#10B981;">●</b> Positif (Mendukung / Apresiasi)</span>
            <span><b style="color:#64748B;">●</b> Netral (Informasi / Berita Formal)</span>
            <span><b style="color:#EF4444;">●</b> Negatif (Kritik / Sentimen Skeptis)</span>
        </div>
        """, unsafe_allow_html=True)

    html_graph = generate_pyvis_html(G, height="600px", mode=sna_mode)
    components_v1.html(html_graph, height=620, scrolling=False)

    st.markdown("---")
    st.markdown("#### 🏆 Tabel Aktor Kunci & Metrik Sentralitas Jaringan")
    
    t_c1, t_c2 = st.columns(2)
    with t_c1:
        st.markdown("##### 🎯 Top Pemengaruh / Otoritas (In-Degree Centrality)")
        st.caption("Akun yang paling sering dijadikan rujukan atau dimention oleh warganet.")
        
        in_deg_table = []
        for n, data in net_metrics['top_in_degree']:
            in_deg_table.append({
                "Akun": f"@{str(n).strip().lstrip('@')}",
                "Klasifikasi": data.get(sna_mode, 'Netral'),
                "In-Degree (Dirujuk)": data.get('in_degree', 0),
                "Out-Degree": data.get('out_degree', 0),
            })
        st.dataframe(pd.DataFrame(in_deg_table), use_container_width=True)

    with t_c2:
        st.markdown("##### 🌉 Top Jembatan Opini (Betweenness Centrality)")
        st.caption("Akun yang menjadi penghubung/broker informasi antar-kluster komunitas.")
        
        bw_table = []
        for n, data in net_metrics['top_betweenness']:
            bw_table.append({
                "Akun": f"@{str(n).strip().lstrip('@')}",
                "Klasifikasi": data.get(sna_mode, 'Netral'),
                "Betweenness Score": data.get('betweenness', 0.0),
                "In-Degree": data.get('in_degree', 0),
            })
        st.dataframe(pd.DataFrame(bw_table), use_container_width=True)

    st.markdown("---")
    try:
        gexf_path = os.path.join(current_dir, "sna", "output", f"{target_topic}_{target_plat}_{sna_mode}_network.gexf")
        os.makedirs(os.path.dirname(gexf_path), exist_ok=True)
        res = export_gephi_gexf(G, gexf_path)
        
        if res and os.path.exists(gexf_path):
            with open(gexf_path, "rb") as f_gexf:
                st.download_button(
                    label="Unduh File Graf Gephi (.GEXF) untuk Analisis Lanjutan di Gephi",
                    data=f_gexf,
                    file_name=f"{target_topic}_{target_plat}_{sna_mode}_sna.gexf",
                    mime="application/xml",
                    icon=":material/download:"
                )
    except Exception as e:
        st.info("File ekspor Gephi (.GEXF) disiapkan saat diminta.")
