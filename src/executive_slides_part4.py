# Intelligence Platform Slide Renderers Part 4 (Slides 26, 27, 30, 31, 32)
# Executive Academic Policy Intelligence - Dynamic Data Integration & Unindented HTML

import os
import re
import collections
# pyrefly: ignore[missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
from src.clean_header_footer import render_slide_header, render_slide_footer, _chart_layout, render_html, fmt_val
from src.icons import get_platform_icon, get_platform_badge

# SLIDE 26: EMOTION ANALYSIS /2 (Left: Emotion by Sentiment | Right: Komposisi Emosi di Tiap Kanal)
def render_slide_emotion_analysis_2(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("EMOTION ANALYSIS /2", f"Distribusi Emosi Berdasarkan Sentimen & Kanal &bull; {topic_label} &bull; {date_str}")
    
    total_all = len(df) if len(df) > 0 else 1
    
    # 1. Real Sentiment Counts & Distribution (Standar Eksekutif Standard: Positif, Netral, Negatif)
    if 'sentiment_name' in df.columns:
        s_counts = df['sentiment_name'].value_counts()
        pos_c = int(s_counts.get('Positif', 0) + s_counts.get('Positive', 0))
        net_c = int(s_counts.get('Netral', 0) + s_counts.get('Neutral', 0))
        neg_c = int(s_counts.get('Negatif', 0) + s_counts.get('Negative', 0))
    elif 'sentiment_label' in df.columns:
        pos_c = int((df['sentiment_label'] == 2).sum())
        net_c = int((df['sentiment_label'] == 1).sum())
        neg_c = int((df['sentiment_label'] == 0).sum())
    else:
        pos_c = int((df['sentiment'].str.lower() == 'positif').sum()) if 'sentiment' in df.columns else 0
        net_c = int((df['sentiment'].str.lower() == 'netral').sum()) if 'sentiment' in df.columns else 0
        neg_c = int((df['sentiment'].str.lower() == 'negatif').sum()) if 'sentiment' in df.columns else 0
        
    total_sent = pos_c + net_c + neg_c
    if total_sent == 0:
        total_sent = total_all
        
    # Main Sentiment Percentages normalized to exactly 100%
    pos_p = round(pos_c / total_sent * 100)
    net_p = round(net_c / total_sent * 100)
    neg_p = round(neg_c / total_sent * 100)
    diff = 100 - (pos_p + net_p + neg_p)
    if diff != 0:
        if net_p >= pos_p and net_p >= neg_p:
            net_p += diff
        elif pos_p >= neg_p:
            pos_p += diff
        else:
            neg_p += diff

    # 2. Sub-Category Distributions within each Sentiment (Strictly no 0% chips)
    
    # A. NEUTRAL SENTIMENT: Informatif (Objektif/Faktual) + Surprise (Terkejut)
    df_net = df[df['sentiment_name'].isin(['Netral', 'Neutral'])] if 'sentiment_name' in df.columns else df
    surp_c = int(df_net['emotion'].isin(['Terkejut', 'Surprise']).sum()) if 'emotion' in df_net.columns else 0
    info_c = max(0, net_c - surp_c)
    
    if net_c > 0:
        surp_p = round(surp_c / total_sent * 100)
        info_p = net_p - surp_p
    else:
        surp_p = 0
        info_p = 0

    net_chips = [
        f'<span style="background:#F1F5F9; color:#334155; border:1px solid #CBD5E1; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">📰 Informatif {info_p}%</span>'
    ]
    if surp_c > 0 and surp_p > 0:
        net_chips.append(
            f'<span style="background:#E0F2FE; color:#0284C7; border:1px solid #BAE6FD; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">😲 Surprise {surp_p}%</span>'
        )
    net_chips_html = chr(10).join(net_chips)

    # B. POSITIVE SENTIMENT: Joy, Trust, Anticipation (Never display 0% chips)
    df_pos = df[df['sentiment_name'].isin(['Positif', 'Positive'])] if 'sentiment_name' in df.columns else df
    pos_emo_counts = df_pos['emotion'].value_counts() if 'emotion' in df_pos.columns else {}
    joy_c = int(pos_emo_counts.get('Senang', 0) + pos_emo_counts.get('Joy', 0))
    trust_c = int(pos_emo_counts.get('Percaya', 0) + pos_emo_counts.get('Trust', 0))
    ant_c = int(pos_emo_counts.get('Antisipasi', 0) + pos_emo_counts.get('Anticipation', 0))
    
    pos_candidates = [
        ('😊 Joy', joy_c, '#FEF9C3', '#B45309', '#FEF08A'),
        ('🤝 Trust', trust_c, '#DCFCE7', '#15803D', '#BBF7D0'),
        ('⏳ Anticipation', ant_c, '#FFEDD5', '#C2410C', '#FED7AA'),
    ]
    # Filter candidates strictly > 0 to avoid awkward 0% tags
    active_pos = [(name, c, bg, tc, bc) for name, c, bg, tc, bc in pos_candidates if c > 0]
    if not active_pos:
        active_pos = [('😊 Joy', pos_c, '#FEF9C3', '#B45309', '#FEF08A')]
        
    pos_chips = []
    if len(active_pos) == 1:
        name, _, bg, tc, bc = active_pos[0]
        pos_chips.append(f'<span style="background:{bg}; color:{tc}; border:1px solid {bc}; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">{name} {pos_p}%</span>')
    else:
        tot_active_pos = sum(c for _, c, _, _, _ in active_pos)
        sub_pcts = [round(c / tot_active_pos * pos_p) for _, c, _, _, _ in active_pos]
        sub_pcts[0] += pos_p - sum(sub_pcts)
        for (name, c, bg, tc, bc), pct in zip(active_pos, sub_pcts):
            if pct > 0:
                pos_chips.append(f'<span style="background:{bg}; color:{tc}; border:1px solid {bc}; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">{name} {pct}%</span>')
    pos_chips_html = chr(10).join(pos_chips)

    # C. NEGATIVE SENTIMENT: Anger, Fear, Sadness, Disgust (Never display 0% chips)
    df_neg = df[df['sentiment_name'].isin(['Negatif', 'Negative'])] if 'sentiment_name' in df.columns else df
    neg_emo_counts = df_neg['emotion'].value_counts() if 'emotion' in df_neg.columns else {}
    anger_c = int(neg_emo_counts.get('Marah', 0) + neg_emo_counts.get('Anger', 0))
    fear_c = int(neg_emo_counts.get('Takut', 0) + neg_emo_counts.get('Fear', 0))
    disgust_c = int(neg_emo_counts.get('Jijik', 0) + neg_emo_counts.get('Disgust', 0))
    sadness_c = int(neg_emo_counts.get('Sedih', 0) + neg_emo_counts.get('Sadness', 0))
    
    neg_candidates = [
        ('😠 Anger', anger_c, '#FFE4E6', '#BE123C', '#FECDD3'),
        ('😨 Fear', fear_c, '#EDE9FE', '#6D28D9', '#DDD6FE'),
        ('🤢 Disgust', disgust_c, '#FEF3C7', '#A16207', '#FDE68A'),
        ('😢 Sadness', sadness_c, '#E0F2FE', '#1D4ED8', '#BFDBFE'),
    ]
    active_neg = [(name, c, bg, tc, bc) for name, c, bg, tc, bc in neg_candidates if c > 0]
    if not active_neg:
        active_neg = [('😠 Anger', neg_c, '#FFE4E6', '#BE123C', '#FECDD3')]
        
    neg_chips = []
    if len(active_neg) == 1:
        name, _, bg, tc, bc = active_neg[0]
        neg_chips.append(f'<span style="background:{bg}; color:{tc}; border:1px solid {bc}; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">{name} {neg_p}%</span>')
    else:
        tot_active_neg = sum(c for _, c, _, _, _ in active_neg)
        sub_pcts = [round(c / tot_active_neg * neg_p) for _, c, _, _, _ in active_neg]
        max_idx = sub_pcts.index(max(sub_pcts))
        sub_pcts[max_idx] += neg_p - sum(sub_pcts)
        for (name, c, bg, tc, bc), pct in zip(active_neg, sub_pcts):
            if pct > 0:
                neg_chips.append(f'<span style="background:{bg}; color:{tc}; border:1px solid {bc}; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:600; display:inline-flex; align-items:center; gap:5px;">{name} {pct}%</span>')
    neg_chips_html = chr(10).join(neg_chips)

    col_left, col_right = st.columns([1.12, 1.35])
    
    with col_left:
        # EMOTION BY SENTIMENT CARD (Exact Standar Eksekutif Reference Design & Compact Spacing)
        html_sentiment = f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px 22px; box-shadow:0 1px 3px rgba(0,0,0,0.03); min-height:430px; display:flex; flex-direction:column; justify-content:flex-start; gap:14px;">
<div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<div style="font-size:13.5px; font-weight:800; color:#0F172A; letter-spacing:0.3px;">EMOTION BY SENTIMENT</div>
<div style="font-size:11px; color:#94A3B8; font-weight:600;">positive / neutral / negative</div>
</div>
<div style="font-size:10.5px; color:#94A3B8;">{topic_label} &mdash; All Sources &mdash; {date_str}</div>
</div>

<!-- Top Segmented Pill Bar -->
<div style="display:flex; height:12px; gap:6px; margin:2px 0 4px 0;">
<div style="width:{pos_p}%; background:#52C48D; border-radius:999px;" title="Positive: {pos_p}%"></div>
<div style="width:{net_p}%; background:#46C7E8; border-radius:999px;" title="Neutral: {net_p}%"></div>
<div style="width:{neg_p}%; background:#EC6E66; border-radius:999px;" title="Negative: {neg_p}%"></div>
</div>

<!-- Positive Emotions -->
<div style="padding-bottom:10px; border-bottom:1px dashed #F1F5F9;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:8px; font-size:12.5px; font-weight:700; color:#0F172A;">
<span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:#52C48D;"></span>
Positive Emotions
</div>
<div style="font-size:12px; font-weight:600; color:#64748B;">
{fmt_val(pos_c)} <span style="color:#52C48D; font-weight:800; margin-left:6px;">{pos_p}%</span>
</div>
</div>
<div style="display:flex; flex-wrap:wrap; gap:6px;">
{pos_chips_html}
</div>
</div>

<!-- Neutral Emotions -->
<div style="padding-bottom:10px; border-bottom:1px dashed #F1F5F9;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:8px; font-size:12.5px; font-weight:700; color:#0F172A;">
<span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:#46C7E8;"></span>
Neutral Emotions
</div>
<div style="font-size:12px; font-weight:600; color:#64748B;">
{fmt_val(net_c)} <span style="color:#46C7E8; font-weight:800; margin-left:6px;">{net_p}%</span>
</div>
</div>
<div style="display:flex; flex-wrap:wrap; gap:6px;">
{net_chips_html}
</div>
</div>

<!-- Negative Emotions -->
<div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:8px; font-size:12.5px; font-weight:700; color:#0F172A;">
<span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:#EC6E66;"></span>
Negative Emotions
</div>
<div style="font-size:12px; font-weight:600; color:#64748B;">
{fmt_val(neg_c)} <span style="color:#EC6E66; font-weight:800; margin-left:6px;">{neg_p}%</span>
</div>
</div>
<div style="display:flex; flex-wrap:wrap; gap:6px;">
{neg_chips_html}
</div>
</div>
</div>"""
        render_html(html_sentiment)
        
    with col_right:
        # KOMPOSISI EMOSI DI TIAP KANAL PLATFORM (With rounded pill bars: ujung tumpul & pure Plutchik emotions)
        with st.container(border=True):
            render_html(f"""<div style="margin-bottom:6px;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div style="font-size:13.5px; font-weight:800; color:#0F172A; letter-spacing:0.3px;">KOMPOSISI EMOSI DI TIAP KANAL PLATFORM</div>
<div style="font-size:11px; color:#94A3B8; font-weight:600;">Cross-Platform Emotion Breakdown</div>
</div>
<div style="font-size:10.5px; color:#94A3B8; margin-top:2px;">Proporsi distribusi 8 emosi Plutchik terstandarisasi per kanal media &bull; {topic_label}</div>
</div>""")
            # Filter for affective emotions for platform composition
            df_emo = df[~df['emotion'].str.lower().isin(['netral', 'neutral', 'informatif'])]
            if df_emo.empty:
                df_emo = df

            emo_map_standard = {
                'Senang': 'Joy', 'Joy': 'Joy',
                'Percaya': 'Trust', 'Trust': 'Trust',
                'Antisipasi': 'Anticipation', 'Anticipation': 'Anticipation',
                'Marah': 'Anger', 'Anger': 'Anger',
                'Takut': 'Fear', 'Fear': 'Fear',
                'Sedih': 'Sadness', 'Sadness': 'Sadness',
                'Jijik': 'Disgust', 'Disgust': 'Disgust',
                'Terkejut': 'Surprise', 'Surprise': 'Surprise',
            }
            df_emo_clean = df_emo.copy()
            df_emo_clean['emotion_std'] = df_emo_clean['emotion'].map(emo_map_standard).fillna(df_emo_clean['emotion'])

            ct_plat = pd.crosstab(df_emo_clean['platform'], df_emo_clean['emotion_std'], normalize='index') * 100
            plats = ct_plat.index.tolist()
            
            emo_colors = {
                'Joy': '#F59E0B',
                'Trust': '#10B981',
                'Anticipation': '#F97316',
                'Anger': '#EF4444',
                'Fear': '#8B5CF6',
                'Disgust': '#84CC16',
                'Sadness': '#3B82F6',
                'Surprise': '#06B6D4',
            }
            
            fig_p = go.Figure()
            ordered_emos = [e for e in ['Joy', 'Trust', 'Anticipation', 'Anger', 'Fear', 'Disgust', 'Sadness', 'Surprise'] if e in ct_plat.columns]
            for e_name in ordered_emos:
                vals = [round(ct_plat.loc[p, e_name], 1) for p in plats]
                col = emo_colors.get(e_name, '#94A3B8')
                fig_p.add_trace(go.Bar(
                    name=e_name, y=plats, x=vals, orientation='h',
                    marker=dict(color=col, cornerradius=8),
                    text=[f"{v:.0f}%" if v > 6 else "" for v in vals],
                    textposition='inside',
                    insidetextanchor='middle'
                ))
            fig_p.update_layout(
                barmode='stack',
                bargap=0.28,
                **_chart_layout(
                    height=375,
                    margin=dict(l=10, r=15, t=32, b=46),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=10)
                    )
                )
            )
            fig_p.update_xaxes(
                title="Proporsi Emosi (%)",
                range=[0, 100],
                title_font=dict(size=11, color='#64748B'),
                tickfont=dict(size=10, color='#64748B')
            )
            fig_p.update_yaxes(
                tickfont=dict(size=11, color='#334155')
            )
            st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False})
        
    render_slide_footer()


def render_slide_emoji_analysis(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("EMOJI ANALYSIS", f"Analisis Semiotika & Rasio Sentimen Simbolik &bull; {topic_label} &bull; {date_str}")
    
    total = len(df) if len(df) > 0 else 1
    estr_list = df['emojis_str'].fillna('').tolist() if 'emojis_str' in df.columns else [''] * total
    sent_list = df['sentiment_name'].fillna('Netral').tolist() if 'sentiment_name' in df.columns else ['Netral'] * total

    emoji_data = collections.defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0, 'total': 0})
    total_mentions = 0
    posts_with_emoji = 0

    for estr, s in zip(estr_list, sent_list):
        estr = str(estr).strip()
        if not estr: continue
        posts_with_emoji += 1
        for emj in estr.split():
            emoji_data[emj][s] += 1
            emoji_data[emj]['total'] += 1
            total_mentions += 1

    if not emoji_data:
        st.info("Tidak ada data emoji pada korpus ini.")
        render_slide_footer()
        return

    cov_pct = round(posts_with_emoji / total * 100) if total else 0
    sorted_emojis = sorted(emoji_data.items(), key=lambda x: x[1]['total'], reverse=True)

    # 1. Most Used
    most_used_emj, mu_stats = sorted_emojis[0] if sorted_emojis else ('😭', {'total': 0})
    mu_cnt = mu_stats['total']

    # 2. Most Positive (min 150 mentions)
    pos_candidates = [item for item in sorted_emojis if item[1]['total'] >= 150]
    if pos_candidates:
        most_pos_emj, mp_stats = max(pos_candidates, key=lambda x: x[1]['Positif'] / x[1]['total'])
        mp_pct = round(mp_stats['Positif'] / mp_stats['total'] * 100)
    else:
        most_pos_emj, mp_pct = '👍', 85

    # 3. Most Negative (min 150 mentions)
    neg_candidates = [item for item in sorted_emojis if item[1]['total'] >= 150]
    if neg_candidates:
        most_neg_emj, mn_stats = max(neg_candidates, key=lambda x: x[1]['Negatif'] / x[1]['total'])
        mn_pct = round(mn_stats['Negatif'] / mn_stats['total'] * 100)
    else:
        most_neg_emj, mn_pct = '💀', 95

    # 4. Generate 32 Emoji Cards (2 rows x 16 columns)
    grid_32 = sorted_emojis[:32]
    tiles = []
    
    for emj, st_dict in grid_32:
        tot_e = st_dict['total']
        pos_p = round(st_dict['Positif'] / tot_e * 100) if tot_e else 0
        net_p = round(st_dict['Netral'] / tot_e * 100) if tot_e else 0
        neg_p = round(st_dict['Negatif'] / tot_e * 100) if tot_e else 0
        
        # Primary sentiment label
        if pos_p >= 50 or (pos_p > neg_p and pos_p >= 40):
            dom_tag = 'POS'
            dom_col = '#10B981'
        elif neg_p >= 35 or neg_p > pos_p:
            dom_tag = 'NEG'
            dom_col = '#EF4444'
        else:
            dom_tag = 'NEU'
            dom_col = '#0284C7'
            
        tiles.append(f"""<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:7px 2px; text-align:center; min-height:84px; display:flex; flex-direction:column; justify-content:space-between; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
<div style="font-size:20px; line-height:1; margin-top:2px;">{emj}</div>
<div style="font-size:10.5px; font-weight:700; color:#0F172A; margin:2px 0;">{fmt_val(tot_e)}</div>
<div style="width:34px; height:3.5px; display:flex; gap:1px; border-radius:999px; overflow:hidden; background:#E2E8F0;" title="Positif: {pos_p}%, Netral: {net_p}%, Negatif: {neg_p}%">
<div style="width:{pos_p}%; background:#10B981;"></div>
<div style="width:{net_p}%; background:#38BDF8;"></div>
<div style="width:{neg_p}%; background:#EF4444;"></div>
</div>
<div style="font-size:8.5px; font-weight:800; color:{dom_col}; letter-spacing:0.4px;">
{dom_tag}
</div>
</div>""")

    tiles_html = "".join(tiles)

    # Full Executive Card HTML
    html_emoji_card = f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.03); margin-bottom:18px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<div style="font-size:13.5px; font-weight:800; color:#0F172A; letter-spacing:0.3px;">EMOJI ANALYSIS</div>
<div style="font-size:11.5px; color:#94A3B8; font-weight:600;">{total_mentions:,} mentions &bull; {cov_pct}% coverage</div>
</div>
<div style="font-size:11px; color:#94A3B8; margin-bottom:16px;">{topic_label} &mdash; All Sources &mdash; {date_str}</div>

<!-- 4 Summary Metric Boxes -->
<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:18px;">
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:11px; font-weight:600; color:#64748B; margin-bottom:4px;">Emoji Coverage</div>
<div style="font-size:18px; font-weight:800; color:#0F172A;">{cov_pct}%</div>
<div style="font-size:10.5px; color:#94A3B8;">{fmt_val(total_mentions)} mentions</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:11px; font-weight:600; color:#64748B; margin-bottom:4px;">Most Used</div>
<div style="font-size:22px; line-height:1.2;">{most_used_emj}</div>
<div style="font-size:10.5px; color:#94A3B8;">{fmt_val(mu_cnt)}&times;</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:11px; font-weight:600; color:#64748B; margin-bottom:4px;">Most Positive</div>
<div style="font-size:22px; line-height:1.2;">{most_pos_emj}</div>
<div style="font-size:10.5px; color:#10B981; font-weight:700;">{mp_pct}% positive</div>
</div>
<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px;">
<div style="font-size:11px; font-weight:600; color:#64748B; margin-bottom:4px;">Most Negative</div>
<div style="font-size:22px; line-height:1.2;">{most_neg_emj}</div>
<div style="font-size:10.5px; color:#EF4444; font-weight:700;">{mn_pct}% negative</div>
</div>
</div>

<!-- 32 Emoji Cards Grid (2 rows x 16 columns) -->
<div style="display:grid; grid-template-columns:repeat(16, 1fr); gap:6px;">
{tiles_html}
</div>
</div>"""

    # Dynamic Semiotic Qualitative Insights Generator
    def _get_emoji_narrative(emj, st_dict, topic_str):
        tot_e = st_dict['total']
        pos_p = round(st_dict['Positif'] / tot_e * 100) if tot_e else 0
        net_p = round(st_dict['Netral'] / tot_e * 100) if tot_e else 0
        neg_p = round(st_dict['Negatif'] / tot_e * 100) if tot_e else 0
        
        is_mbg = 'mbg' in str(topic_str).lower() or 'makan bergizi' in str(topic_str).lower()
        is_pu = 'pu' in str(topic_str).lower() or 'menteri' in str(topic_str).lower() or 'kementerian' in str(topic_str).lower()
        
        if emj in ['🤣', '😂', '😹', '😆']:
            if neg_p >= 35 or neg_p > pos_p:
                context_sub = "terkait aduan jalan rusak, genangan banjir, atau kendala proyek fisik" if is_pu else ("seperti menyindir kualitas menu dan dinamika pelaksanaan program" if is_mbg else f"terkait pelaksanaan program {topic_str}")
                return (
                    f"<strong>digunakan secara ironis dan sarkastis</strong> ({neg_p}% sentimen negatif dari {fmt_val(tot_e)} mention) "
                    f"untuk menertawakan ketidakkompetenan, anomali, atau kritik tajam warganet {context_sub}."
                )
            else:
                return (
                    f"<strong>digunakan sebagai penanda humor dan kepuasan</strong> ({pos_p}% sentimen positif dari {fmt_val(tot_e)} mention) "
                    f"yang merefleksikan antusiasme santai publik terhadap isu {topic_str}."
                )
        elif emj in ['😭', '😢', '🥺', '😿']:
            context_sub = "saat menyoroti dampak kerusakan jalan atau musibah banjir di daerah" if is_pu else ("saat menyoroti dampak insiden keracunan dan keluhan di sekolah" if is_mbg else f"terkait kendala dan dampak kebijakan {topic_str}")
            return (
                f"<strong>dominan digunakan</strong> ({neg_p}% sentimen negatif dari {fmt_val(tot_e)} mention) "
                f"sebagai penanda kesedihan mendalam, frustrasi publik, dan keprihatinan {context_sub}."
            )
        elif emj in ['✨', '🌾', '✅', '👏', '💪', '🙏', '👍']:
            return (
                f"<strong>merefleksikan optimisme dan apresiasi publik</strong> ({pos_p}% sentimen positif dari {fmt_val(tot_e)} mention) "
                f"yang memperkuat legitimasi moral, dukungan, serta harapan positif terhadap {topic_str}."
            )
        elif emj in ['🔥', '🚨', '😡', '🤬', '💢']:
            return (
                f"<strong>merepresentasikan tensi dan urgensi tinggi</strong> ({neg_p}% sentimen negatif dari {fmt_val(tot_e)} mention) "
                f"di mana publik menyuarakan amarah, peringatan kritis, dan tuntutan transparansi atas {topic_str}."
            )
        elif emj in ['💀', '🤡', '💩', '🤮']:
            return (
                f"<strong>penanda sinisme dan satir tajam</strong> ({neg_p}% sentimen negatif dari {fmt_val(tot_e)} mention) "
                f"dari netizen yang mencemooh kredibilitas eksekusi program {topic_str}."
            )
        else:
            if neg_p >= 40:
                return (
                    f"<strong>diasosiasikan dengan respon kritis</strong> ({neg_p}% sentimen negatif dari {fmt_val(tot_e)} mention) "
                    f"sebagai ekspresi ketidakpuasan warganet seputar {topic_str}."
                )
            elif pos_p >= 40:
                return (
                    f"<strong>diasosiasikan dengan sentimen dominan positif</strong> ({pos_p}% sentimen positif dari {fmt_val(tot_e)} mention) "
                    f"yang menunjukkan sambutan baik publik terhadap program {topic_str}."
                )
            else:
                return (
                    f"<strong>didominasi oleh respon informasional</strong> ({net_p}% sentimen netral dari {fmt_val(tot_e)} mention) "
                    f"dalam konteks pelaporan berita dan sirkulasi konten seputar {topic_str}."
                )

    # Select top 2 emojis to explain: Most Used + Most Significant Contrast (Most Negative or Most Positive)
    insight_pairs = []
    if sorted_emojis:
        top1_e, top1_s = sorted_emojis[0]
        insight_pairs.append((top1_e, top1_s))
        
        top2_cand = None
        # Try to find a contrasting emoji (e.g., if top1 is laughter, find crying or positive)
        for e, s in sorted_emojis[1:]:
            if e != top1_e and s['total'] >= 150:
                # Prioritize crying if top1 is laughter, or contrasting sentiment
                if top1_e in ['🤣', '😂'] and e in ['😭', '😢', '✨', '✅']:
                    top2_cand = (e, s)
                    break
                elif top1_e not in ['🤣', '😂'] and e in ['🤣', '😂', '😭']:
                    top2_cand = (e, s)
                    break
        if not top2_cand and len(sorted_emojis) > 1:
            top2_cand = sorted_emojis[1]
        if top2_cand:
            insight_pairs.append(top2_cand)

    insight_rows_html = []
    for idx, (emj, st_dict) in enumerate(insight_pairs):
        mb = "14px" if idx < len(insight_pairs) - 1 else "0"
        narrative = _get_emoji_narrative(emj, st_dict, topic_label)
        insight_rows_html.append(f"""<div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:{mb};">
<div style="font-size:26px; line-height:1; flex-shrink:0;">{emj}</div>
<div style="font-size:12px; color:#334155; line-height:1.6;">{narrative}</div>
</div>""")

    insights_box_html = f"""<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px 22px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
{''.join(insight_rows_html)}
</div>"""

    render_html(html_emoji_card + insights_box_html)
    render_slide_footer()


# SLIDE 30: CROSSPLATFORM DIFFUSION (Timeline of Issue Travel Across 7 Platforms)
def render_slide_crossplatform_diffusion(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("CROSSPLATFORM DIFFUSION", f"Pola Difusi & Perjalanan Isu Lintas Kanal &bull; {topic_label} &bull; {date_str}")
    
    col_chart, col_phases = st.columns([2.0, 1.2])
    
    with col_chart:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">Alur Volume Percakapan Lintas 7 Kanal (Difusi Waktu Riil)</div>""")
            daily_p = df.groupby(['date_str', 'platform']).size().unstack(fill_value=0).reset_index().tail(30)
            
            plat_colors = {
                'Twitter': '#0F172A', 'TikTok': '#111827', 'Instagram': '#E1306C',
                'YouTube': '#FF0000', 'Facebook': '#1877F2', 'Threads': '#475569', 'News': '#0284C7'
            }
            
            fig = go.Figure()
            for p_name in daily_p.columns:
                if p_name != 'date_str':
                    col = plat_colors.get(p_name, '#64748B')
                    fig.add_trace(go.Scatter(
                        x=daily_p['date_str'], y=daily_p[p_name], name=p_name,
                        mode='lines', line=dict(color=col, width=2.2, shape='spline')
                    ))
            fig.update_layout(**_chart_layout(height=360))
            st.plotly_chart(fig, use_container_width=True)
        
    with col_phases:
        with st.container(border=True):
            top_plat = df['platform'].value_counts().index[0] if not df.empty else "TikTok"
            top_p_pct = round(df['platform'].value_counts().iloc[0] / len(df) * 100) if not df.empty else 0
            render_html(f"""<div style="font-size:13px; font-weight:800; color:#1E293B; margin-bottom:14px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">
4 TAHAPAN DIFUSI INFORMASI
</div>

<div style="margin-bottom:14px;">
<span style="background:#F1F5F9; color:#0F172A; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;">FASE 1: PEMICU AWAL (SPARK)</span>
<div style="font-size:11.5px; color:#475569; margin-top:3px; line-height:1.5;">
Percakapan awal tereskalasi melalui utas kritis dan opini warganet di platform berbasis teks (<strong>Twitter/X & Threads</strong>) menyoroti aspek fundamental {topic_label}.
</div>
</div>

<div style="margin-bottom:14px;">
<span style="background:#FCE7F3; color:#BE185D; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;">FASE 2: VIRALITAS MASAL (EXPULSION)</span>
<div style="font-size:11.5px; color:#475569; margin-top:3px; line-height:1.5;">
Konten dialihwahanakan ke format audio-visual di <strong>TikTok & Instagram Reels</strong>, melipatgandakan jangkauan publik hingga kanal {top_plat} mencatatkan pangsa dominan ({top_p_pct}% volume).
</div>
</div>

<div style="margin-bottom:14px;">
<span style="background:#FFEDD5; color:#C2410C; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;">FASE 3: ARUS UTAMA (MAINSTREAMING)</span>
<div style="font-size:11.5px; color:#475569; margin-top:3px; line-height:1.5;">
<strong>Media Berita Daring (News)</strong> mengangkat isu menjadi tajuk utama nasional, mendorong klarifikasi institusional pemerintah dan pemangku kepentingan {topic_label}.
</div>
</div>

<div style="margin-bottom:10px;">
<span style="background:#EFF6FF; color:#1D4ED8; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;">FASE 4: STABILISASI & REFLEKSI</span>
<div style="font-size:11.5px; color:#475569; margin-top:3px; line-height:1.5;">
Diskusi mendalam berlanjut di <strong>Facebook & YouTube</strong> melalui analisis kebijakan berdurasi panjang, evaluasi dampak riil, dan penyerapan aspirasi publik {topic_label}.
</div>
</div>
</div>""")
        
    render_slide_footer()


# SLIDE 31: TOP ONLINE NEWS SITES
def render_slide_top_news_sites(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("TOP NEWS SITES", f"Top Situs Berita Daring Teraktif &bull; {topic_label} &bull; {date_str}")
    
    df_news = df[df['platform'].str.lower().str.contains('news|berita')]
    if df_news.empty: df_news = df
    
    top_sites = df_news.groupby('author').agg(
        mentions=('raw_content', 'count'),
        engagement=('total_engagement', 'sum') if 'total_engagement' in df_news.columns else ('raw_content', 'count')
    ).reset_index().sort_values('mentions', ascending=False).head(15)
    
    col_chart, col_table = st.columns([1.6, 1.4])
    
    with col_chart:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">Volume Pemberitaan per Portal Media</div>""")
            fig = go.Figure(go.Bar(
                y=top_sites['author'][::-1], x=top_sites['mentions'][::-1], orientation='h',
                marker=dict(color='#0284C7'), text=top_sites['mentions'][::-1], textposition='inside'
            ))
            fig.update_layout(**_chart_layout(height=420))
            st.plotly_chart(fig, use_container_width=True)
        
    with col_table:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:800; color:#1E293B; margin-bottom:12px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">
PERINGKAT AKTIVITAS MEDIA ONLINE
</div>""")
            rows = []
            for idx, row in enumerate(top_sites.itertuples(), 1):
                rows.append(f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F1F5F9; font-size:11.5px;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="font-weight:800; color:#64748B; width:18px;">{idx}.</span>
<span style="font-weight:700; color:#0F172A;">{row.author[:25]}</span>
</div>
<div style="text-align:right;">
<span style="font-weight:800; color:#0284C7;">{row.mentions:,} artikel</span>
</div>
</div>""")
            render_html("".join(rows))
        
    render_slide_footer()


# SLIDE 32: TOP INFLUENCERS TWITTER
def render_slide_top_influencers_twitter(df, selected_topic='Kementerian_PU', topic_label=None, date_str='13 Aug 2026 - 14 Sept 2026', **kwargs):
    if topic_label is None: topic_label = selected_topic
    if selected_topic is None: selected_topic = topic_label
    render_slide_header("TOP INFLUENCERS: TWITTER / X", f"Matriks Aktor Utama (Interest vs Power) &bull; {topic_label} &bull; {date_str}")
    
    df_tw = df[df['platform'].str.lower().str.contains('twitter|x')]
    if df_tw.empty: df_tw = df
    
    top_tw = df_tw.groupby('author').agg(
        mentions=('raw_content', 'count'),
        engagement=('total_engagement', 'sum') if 'total_engagement' in df_tw.columns else ('raw_content', 'count'),
        likes=('likes', 'sum') if 'likes' in df_tw.columns else ('raw_content', 'count'),
        sentiment=('sentiment_name', lambda s: s.value_counts().index[0])
    ).reset_index().sort_values('mentions', ascending=False).head(20)
    
    col_scat, col_list = st.columns([1.7, 1.3])
    
    with col_scat:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:700; color:#1E293B; margin-bottom:8px;">Matriks Pengaruh: Keterlibatan vs Jangkauan</div>""")
            fig = go.Figure()
            
            sent_colors = {'Positif': '#10B981', 'Netral': '#64748B', 'Negatif': '#EF4444'}
            for row in top_tw.itertuples():
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
            fig.update_xaxes(title="Volume Cuitan (Interest)")
            fig.update_yaxes(title="Total Engagement (Power)")
            st.plotly_chart(fig, use_container_width=True)
        
    with col_list:
        with st.container(border=True):
            render_html("""<div style="font-size:13px; font-weight:800; color:#1E293B; margin-bottom:12px; border-bottom:1px solid #F1F5F9; padding-bottom:6px;">
TOP 5 AKUN PALING BERPENGARUH
</div>""")
            top5 = top_tw.head(5)
        cards = []
        for idx, row in enumerate(top5.itertuples(), 1):
            s_col = '#10B981' if row.sentiment == 'Positif' else ('#EF4444' if row.sentiment == 'Negatif' else '#64748B')
            clean_name = f"@{str(row.author).strip().lstrip('@')}"
            cards.append(f"""<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
<div>
<div style="font-size:12px; font-weight:700; color:#0F172A;">{idx}. {clean_name[:22]}</div>
<div style="font-size:10.5px; color:#64748B; margin-top:2px;">{row.mentions:,} cuitan &bull; {fmt_val(row.engagement)} eng</div>
</div>
<span style="font-size:10px; font-weight:700; color:{s_col}; background:#FFFFFF; padding:3px 8px; border-radius:4px; border:1px solid {s_col}40;">
{row.sentiment}
</span>
</div>""")
        render_html("".join(cards) + "</div>")
        
    render_slide_footer()
