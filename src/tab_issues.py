# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
from src.components import (
    extract_top_issues,
    plot_crossplatform_diffusion,
    get_top_terms,
    get_top_hashtags,
)
from src.clean_header_footer import fmt_val

def _get_top_posts_with_links(sub_df, n=10):
    if len(sub_df) == 0:
        return pd.DataFrame()
    sorted_sub = sub_df.sort_values('total_engagement', ascending=False)
    seen_urls = set()
    seen_auth_eng = set()
    chosen_indices = []
    for idx, row in sorted_sub.iterrows():
        url = str(row.get('url', '')).strip().replace('/photo/', '/video/')
        auth = str(row.get('author', '')).strip().lower()
        eng = int(row.get('total_engagement', 0))
        plat = str(row.get('platform', ''))
        
        if len(url) > 10 and url in seen_urls:
            continue
        if auth and eng > 0 and (plat, auth, eng) in seen_auth_eng:
            continue
            
        if len(url) > 10:
            seen_urls.add(url)
        if auth and eng > 0:
            seen_auth_eng.add((plat, auth, eng))
            
        chosen_indices.append(idx)
        if len(chosen_indices) >= n:
            break
    return sorted_sub.loc[chosen_indices]

def render_tab_issues(df_filtered):
    st.subheader("🔍 Top Isu & Pola Difusi Lintas Platform (Issue Diffusion)")
    st.caption("Bagaimana narasi berkembang, menguat, dan berpindah antar-platform media sosial dan berita.")

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

    # -------------------------------------------------------------
    # SOLUSI & REKOMENDASI TINDAKAN STRATEGIS TERKAIT ISU YANG NAIK
    # -------------------------------------------------------------
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="background:#EF4444; color:#FFFFFF; font-size:10.5px; font-weight:800; padding:2px 8px; border-radius:4px; letter-spacing:0.5px;">SOLUSI & MITIGASI</span>
            <span style="font-size:14px; font-weight:700; color:#0F2942;">Rekomendasi Tindakan Strategis Terkait Isu yang Sedang Naik</span>
        </div>
        """, unsafe_allow_html=True)

        # Analisis isu yang paling banyak menimbulkan sentimen negatif
        col_sent = 'sentiment_name' if 'sentiment_name' in df_filtered.columns else 'predicted_sentiment'
        df_neg_issues = df_filtered[df_filtered[col_sent] == 'Negatif'] if col_sent in df_filtered.columns else df_filtered

        # Ekstraksi kategori isu dominan
        from src.tab_sentiment_drilldown import extract_issue_category, get_issue_solution
        if 'issue_category' not in df_neg_issues.columns:
            df_neg_issues = df_neg_issues.copy()
            df_neg_issues['issue_category'] = df_neg_issues['cleaned_content'].fillna(df_neg_issues.get('raw_content', '')).apply(extract_issue_category)

        top_neg_issues = df_neg_issues['issue_category'].value_counts()
        if not top_neg_issues.empty:
            rising_issue_1 = top_neg_issues.index[0]
            count_1 = top_neg_issues.iloc[0]
            sol_1 = get_issue_solution(rising_issue_1)

            rising_issue_2 = top_neg_issues.index[1] if len(top_neg_issues) > 1 else None
            sol_2 = get_issue_solution(rising_issue_2) if rising_issue_2 else None

            c_sol1, c_sol2 = st.columns(2)
            with c_sol1:
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #EF4444; border-radius:8px; padding:12px 14px; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size:11px; font-weight:800; color:#EF4444; background:#FEF2F2; padding:2px 8px; border-radius:4px;">PRIORITAS 1: {rising_issue_1.upper()} ({count_1:,} komplain)</span>
                        <span style="font-size:10px; font-weight:700; color:#64748B;">SLA: {sol_1['sla']}</span>
                    </div>
                    <div style="font-size:11.5px; font-weight:700; color:#0F2942; margin-bottom:4px;">Penanggung Jawab: {sol_1['unit']}</div>
                    <div style="font-size:11.5px; color:#334155; line-height:1.5; margin-bottom:6px;"><strong>Solusi:</strong> {sol_1['tindakan']}</div>
                    <div style="font-size:10.5px; color:#64748B;"><strong>Locus Utama:</strong> {sol_1['target']}</div>
                </div>
                """, unsafe_allow_html=True)

            with c_sol2:
                if sol_2:
                    count_2 = top_neg_issues.iloc[1]
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #D97706; border-radius:8px; padding:12px 14px; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-size:11px; font-weight:800; color:#D97706; background:#FFFBEB; padding:2px 8px; border-radius:4px;">PRIORITAS 2: {rising_issue_2.upper()} ({count_2:,} komplain)</span>
                            <span style="font-size:10px; font-weight:700; color:#64748B;">SLA: {sol_2['sla']}</span>
                        </div>
                        <div style="font-size:11.5px; font-weight:700; color:#0F2942; margin-bottom:4px;">Penanggung Jawab: {sol_2['unit']}</div>
                        <div style="font-size:11.5px; color:#334155; line-height:1.5; margin-bottom:6px;"><strong>Solusi:</strong> {sol_2['tindakan']}</div>
                        <div style="font-size:10.5px; color:#64748B;"><strong>Locus Utama:</strong> {sol_2['target']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Isu negatif lain berada pada level ambang batas normal.")

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

    st.markdown("---")
    st.subheader("🔗 Postingan Paling Berpengaruh (Top Isu dengan Tautan Langsung)")
    st.caption("Daftar postingan publik dengan interaksi tertinggi yang menjadi motor penggerak sentimen positif dan negatif. Klik tombol untuk membuka postingan asli langsung di platform bersangkutan.")

    tab_pos, tab_neg = st.tabs(["⭐ Top Isu Positif (Pengangkat Citra)", "⚠️ Top Isu Negatif (Keluhan & Kritik Viral)"])
    
    col_sentiment = 'sentiment_name' if 'sentiment_name' in df_filtered.columns else 'predicted_sentiment'
    df_pos = df_filtered[df_filtered[col_sentiment] == 'Positif'] if col_sentiment in df_filtered.columns else pd.DataFrame()
    df_neg = df_filtered[df_filtered[col_sentiment] == 'Negatif'] if col_sentiment in df_filtered.columns else pd.DataFrame()
    
    def _format_date_clean(raw_d):
        if not raw_d or pd.isna(raw_d) or str(raw_d).lower() == 'nan':
            return ""
        s = str(raw_d).replace(' WIB', '').replace(' WITA', '').replace(' WIT', '').strip()
        try:
            dt = pd.to_datetime(s, errors='coerce')
            if pd.notna(dt):
                return dt.strftime('%d %b %Y')
        except Exception:
            pass
        import re
        m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
        if m:
            try:
                dt = pd.to_datetime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
                return dt.strftime('%d %b %Y')
            except Exception:
                pass
        return s[:10]

    top_pos_df = _get_top_posts_with_links(df_pos, n=10)
    top_neg_df = _get_top_posts_with_links(df_neg, n=10)
    
    with tab_pos:
        if len(top_pos_df) > 0:
            for idx, (_, r) in enumerate(top_pos_df.iterrows(), 1):
                p_url = str(r.get('url', '')).strip()
                p_plat = str(r.get('platform', 'Sosial Media'))
                p_auth = str(r.get('author', 'Anonim'))
                p_dt = _format_date_clean(r.get('created_at', str(r.get('date_str', ''))))
                p_eng = fmt_val(r.get('total_engagement', 0))
                p_txt = str(r.get('cleaned_content', str(r.get('raw_content', ''))))
                p_emo = str(r.get('emotion', 'Neutral'))
                likes = int(r.get('likes', 0) or 0)
                comments = int(r.get('comments', 0) or 0)
                shares = int(r.get('shares', 0) or 0)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10B981; border-radius:8px; padding:14px 16px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:6px;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span style="background:#DCFCE7; color:#15803D; font-weight:700; font-size:11px; padding:3px 9px; border-radius:4px;">#{idx} {p_plat}</span>
                                <strong style="font-size:13px; color:#0F2942;">@{p_auth}</strong>
                                <span style="font-size:11px; color:#64748B;">• {p_dt}</span>
                            </div>
                            <div style="font-size:12px; font-weight:700; color:#10B981;">
                                {p_eng} Interaksi • Emosi: {p_emo}
                            </div>
                        </div>
                        <div style="font-size:12.5px; color:#1E293B; line-height:1.55; margin-bottom:10px;">
                            "{p_txt}"
                        </div>
                        <div style="font-size:11px; color:#64748B; display:flex; gap:14px; margin-bottom:8px;">
                            <span>❤️ {likes:,} Likes</span>
                            <span>💬 {comments:,} Comments</span>
                            <span>🔄 {shares:,} Shares/Reposts</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if p_url.startswith('http'):
                        st.link_button(f"🌐 Buka Postingan #{idx} di {p_plat} (@{p_auth})", p_url, key=f"btn_tab_pos_{idx}")
        else:
            st.info("Tidak ada data postingan positif.")

    with tab_neg:
        if len(top_neg_df) > 0:
            for idx, (_, r) in enumerate(top_neg_df.iterrows(), 1):
                p_url = str(r.get('url', '')).strip()
                p_plat = str(r.get('platform', 'Sosial Media'))
                p_auth = str(r.get('author', 'Anonim'))
                p_dt = _format_date_clean(r.get('created_at', str(r.get('date_str', ''))))
                p_eng = fmt_val(r.get('total_engagement', 0))
                p_txt = str(r.get('cleaned_content', str(r.get('raw_content', ''))))
                p_emo = str(r.get('emotion', 'Neutral'))
                likes = int(r.get('likes', 0) or 0)
                comments = int(r.get('comments', 0) or 0)
                shares = int(r.get('shares', 0) or 0)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #EF4444; border-radius:8px; padding:14px 16px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:6px;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span style="background:#FEE2E2; color:#B91C1C; font-weight:700; font-size:11px; padding:3px 9px; border-radius:4px;">#{idx} {p_plat}</span>
                                <strong style="font-size:13px; color:#0F2942;">@{p_auth}</strong>
                                <span style="font-size:11px; color:#64748B;">• {p_dt}</span>
                            </div>
                            <div style="font-size:12px; font-weight:700; color:#EF4444;">
                                {p_eng} Interaksi • Emosi: {p_emo}
                            </div>
                        </div>
                        <div style="font-size:12.5px; color:#1E293B; line-height:1.55; margin-bottom:10px;">
                            "{p_txt}"
                        </div>
                        <div style="font-size:11px; color:#64748B; display:flex; gap:14px; margin-bottom:8px;">
                            <span>❤️ {likes:,} Likes</span>
                            <span>💬 {comments:,} Comments</span>
                            <span>🔄 {shares:,} Shares/Reposts</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if p_url.startswith('http'):
                        st.link_button(f"🌐 Buka Postingan #{idx} di {p_plat} (@{p_auth})", p_url, key=f"btn_tab_neg_{idx}")
        else:
            st.info("Tidak ada data postingan negatif.")
