# pyrefly: ignore[missing-import]
import plotly.express as px
# pyrefly: ignore[missing-import]
import plotly.graph_objects as go
# pyrefly: ignore[missing-import]
from plotly.subplots import make_subplots
import pandas as pd
# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
from wordcloud import WordCloud
# pyrefly: ignore[missing-import]
import matplotlib
matplotlib.use('Agg')
# pyrefly: ignore[missing-import]
import matplotlib.pyplot as plt
import io
import base64
import re
from collections import Counter

# ======================================================================
# COLOR PALETTE (Executive Dark Theme)
# ======================================================================
COLORS = {
    'Positif': '#10B981',
    'Netral': '#64748B',
    'Negatif': '#EF4444',
    'bg_dark': '#0F172A',
    'bg_card': '#1E293B',
    'border': '#334155',
    'text_primary': '#F8FAFC',
    'text_secondary': '#94A3B8',
    'accent_blue': '#38BDF8',
    'accent_purple': '#A78BFA',
    'accent_amber': '#F59E0B',
    'accent_pink': '#F472B6',
    'accent_cyan': '#22D3EE',
}

SENTIMENT_COLORS = ['#10B981', '#64748B', '#EF4444']
EMOTION_COLORS = {
    # Positif
    'Joy': '#10B981',
    'Senang': '#10B981',
    'Percaya': '#06B6D4',
    'Trust': '#06B6D4',
    'Antisipasi': '#F59E0B',
    'Anticipation': '#F59E0B',
    # Negatif
    'Marah': '#EF4444',
    'Anger': '#EF4444',
    'Takut': '#8B5CF6',
    'Fear': '#8B5CF6',
    'Jijik': '#84CC16',
    'Disgust': '#84CC16',
    'Sedih': '#3B82F6',
    'Sadness': '#3B82F6',
    # Netral
    'Surprise': '#A78BFA',
    'Terkejut': '#A78BFA',
    'Informatif': '#64748B',
    'Netral': '#64748B',
    'Neutral': '#64748B',
}

PLATFORM_COLORS = {
    'Twitter': '#1DA1F2',
    'Facebook': '#1877F2',
    'Instagram': '#E4405F',
    'YouTube': '#FF0000',
    'TikTok': '#00F2EA',
    'Threads': '#000000',
    'News': '#F59E0B',
}

PLATFORM_ICONS = {
    'Twitter': 'X',
    'Facebook': 'FB',
    'Instagram': 'IG',
    'YouTube': 'YT',
    'TikTok': 'TT',
    'Threads': 'TH',
    'News': 'NW',
}

STOPWORDS_ID = {
    'dan', 'yang', 'di', 'ini', 'itu', 'ke', 'dari', 'untuk', 'pada', 'dengan',
    'adalah', 'akan', 'atau', 'juga', 'dalam', 'bisa', 'ada', 'tidak', 'sudah',
    'karena', 'oleh', 'saat', 'para', 'seperti', 'lebih', 'harus', 'kami', 'kita',
    'bagi', 'saja', 'masih', 'tentang', 'kemenpu', 'kementerian', 'pekerjaan', 'umum',
    'menteri', 'pu', 'pupr', 'kemenpupr', 'program', 'pemerintah', 'ri', 'indonesia',
    'pemerintah', 'https', 'http', 'www', 'com', 'rt', 'amp', 'nan', 'none',
    'telah', 'mereka', 'ia', 'tersebut', 'kata', 'agar', 'lalu', 'maka', 'namun',
    'serta', 'pun', 'yakni', 'antara', 'setiap', 'tetapi', 'hingga', 'secara',
    'bahwa', 'atas', 'nya', 'se', 'tak', 'yg', 'gak', 'ga', 'gk', 'udah', 'dah',
    'lah', 'dong', 'kok', 'sih', 'kan', 'tuh', 'nih', 'deh', 'ya', 'lo', 'gue',
    'lu', 'gw', 'begitu',
}


def _base_layout(height=320, **kwargs):
    layout = dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=30, b=30, l=30, r=30),
        height=height,
        font=dict(family='Inter, sans-serif', color=COLORS['text_secondary']),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1,
            font=dict(color=COLORS['text_secondary'], size=11),
        ),
        xaxis=dict(showgrid=False, color=COLORS['text_secondary']),
        yaxis=dict(gridcolor=COLORS['border'], color=COLORS['text_secondary']),
    )
    layout.update(kwargs)
    return layout


# ======================================================================
# 1. OVERALL SENTIMENT DONUT + NSS
# ======================================================================
def plot_sentiment_donut(df, nss_score):
    counts = df['sentiment_name'].value_counts()
    pos = counts.get('Positif', 0)
    net = counts.get('Netral', 0)
    neg = counts.get('Negatif', 0)

    fig = go.Figure(data=[go.Pie(
        labels=['Positif', 'Netral', 'Negatif'],
        values=[pos, net, neg],
        hole=.65,
        marker=dict(colors=SENTIMENT_COLORS, line=dict(color=COLORS['bg_dark'], width=2)),
        textinfo='percent+label',
        textfont=dict(size=12, color=COLORS['text_primary']),
        hoverinfo='label+value+percent',
    )])

    nss_color = COLORS['Positif'] if nss_score >= 0 else COLORS['Negatif']
    sign = '+' if nss_score > 0 else ''

    fig.update_layout(
        showlegend=False,
        **_base_layout(height=280),
        annotations=[dict(
            text=f"<b style='font-size:16px;color:{COLORS['text_secondary']};'>NSS</b><br>"
                 f"<span style='font-size:28px;color:{nss_color};font-weight:800;'>{sign}{nss_score}</span>",
            x=0.5, y=0.5, font_size=14, showarrow=False,
        )],
    )
    return fig


# ======================================================================
# 2. MENTIONS TREND BY SENTIMENT (Stacked Bar + 7D MA)
# ======================================================================
def plot_mentions_trend_sentiment(df):
    daily = df.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index()
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily = daily.sort_values('date')

    for s in ['Positif', 'Netral', 'Negatif']:
        if s not in daily.columns:
            daily[s] = 0

    daily['Total'] = daily['Positif'] + daily['Netral'] + daily['Negatif']
    daily['7D_MA'] = daily['Total'].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()
    for sent, color in [('Positif', COLORS['Positif']), ('Netral', COLORS['Netral']), ('Negatif', COLORS['Negatif'])]:
        fig.add_trace(go.Bar(x=daily['date'], y=daily[sent], name=sent, marker_color=color))

    fig.add_trace(go.Scatter(
        x=daily['date'], y=daily['7D_MA'],
        name='7-Day Moving Average',
        line=dict(color=COLORS['accent_blue'], width=3),
    ))

    fig.update_layout(barmode='stack', **_base_layout(height=350))
    return fig


# ======================================================================
# 3. MENTIONS TREND BY CHANNEL
# ======================================================================
def plot_mentions_trend_channel(df):
    daily = df.groupby(['date_str', 'platform']).size().unstack(fill_value=0).reset_index()
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily = daily.sort_values('date')

    fig = go.Figure()
    for plat in sorted(df['platform'].unique()):
        if plat in daily.columns:
            color = PLATFORM_COLORS.get(plat, '#64748B')
            fig.add_trace(go.Scatter(
                x=daily['date'], y=daily[plat],
                name=plat, mode='lines',
                line=dict(color=color, width=2),
                stackgroup='one',
            ))

    fig.update_layout(**_base_layout(height=350))
    return fig


# ======================================================================
# 4. MENTIONS TREND BY EMOTIONS
# ======================================================================
def plot_mentions_trend_emotion(df):
    daily = df.groupby(['date_str', 'emotion']).size().unstack(fill_value=0).reset_index()
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily = daily.sort_values('date')

    fig = go.Figure()
    for emo in ['Senang', 'Sedih', 'Marah', 'Takut', 'Terkejut', 'Jijik', 'Netral']:
        if emo in daily.columns:
            color = EMOTION_COLORS.get(emo, '#64748B')
            fig.add_trace(go.Bar(x=daily['date'], y=daily[emo], name=emo, marker_color=color))

    fig.update_layout(barmode='stack', **_base_layout(height=350))
    return fig


# ======================================================================
# 5. PLATFORM SENTIMENT BARS (horizontal)
# ======================================================================
def plot_platform_sentiment_bars(df):
    plat_sent = df.groupby(['platform', 'sentiment_name']).size().unstack(fill_value=0)
    for col in ['Positif', 'Netral', 'Negatif']:
        if col not in plat_sent.columns:
            plat_sent[col] = 0
    plat_sent['Total'] = plat_sent.sum(axis=1)
    plat_sent = plat_sent.sort_values('Total', ascending=True)

    fig = go.Figure()
    for sent, color in [('Positif', COLORS['Positif']), ('Netral', COLORS['Netral']), ('Negatif', COLORS['Negatif'])]:
        fig.add_trace(go.Bar(
            y=plat_sent.index, x=plat_sent[sent],
            name=sent, orientation='h', marker_color=color,
        ))

    fig.update_layout(barmode='stack', **_base_layout(height=300))
    return fig


# ======================================================================
# 6. SENTIMENT PER PLATFORM DONUT (for individual platform pages)
# ======================================================================
def plot_platform_sentiment_donut(df, platform_name):
    sub = df[df['platform'] == platform_name]
    counts = sub['sentiment_name'].value_counts()
    pos = counts.get('Positif', 0)
    net = counts.get('Netral', 0)
    neg = counts.get('Negatif', 0)
    total = pos + net + neg
    nss = round(((pos - neg) / total) * 100, 2) if total > 0 else 0

    fig = go.Figure(data=[go.Pie(
        labels=['Positif', 'Netral', 'Negatif'],
        values=[pos, net, neg],
        hole=.6,
        marker=dict(colors=SENTIMENT_COLORS),
        textinfo='percent+label',
        textfont=dict(size=11, color=COLORS['text_primary']),
    )])

    nss_color = COLORS['Positif'] if nss >= 0 else COLORS['Negatif']
    sign = '+' if nss > 0 else ''

    fig.update_layout(
        showlegend=False,
        **_base_layout(height=220),
        annotations=[dict(
            text=f"<b style='font-size:13px;color:{COLORS['text_secondary']};'>NSS</b><br>"
                 f"<span style='font-size:22px;color:{nss_color};font-weight:800;'>{sign}{nss}</span>",
            x=0.5, y=0.5, font_size=12, showarrow=False,
        )],
    )
    return fig


# ======================================================================
# 7. EMOTION ANALYSIS (Pie + Bar)
# ======================================================================
def plot_emotion_distribution(df):
    emo_counts = df['emotion'].value_counts()
    colors_list = [EMOTION_COLORS.get(e, '#64748B') for e in emo_counts.index]

    fig = go.Figure(data=[go.Pie(
        labels=emo_counts.index.tolist(),
        values=emo_counts.values.tolist(),
        hole=.5,
        marker=dict(colors=colors_list),
        textinfo='percent+label',
        textfont=dict(size=11, color=COLORS['text_primary']),
    )])

    fig.update_layout(showlegend=True, **_base_layout(height=300))
    return fig


def plot_emotion_by_platform(df):
    cross = pd.crosstab(df['platform'], df['emotion'])
    fig = go.Figure()
    all_emotions = [
        'Joy', 'Trust', 'Anticipation', 'Surprise', 'Neutral', 'Disgust', 'Fear', 'Sadness', 'Anger',
        'Senang', 'Marah', 'Sedih', 'Takut', 'Terkejut', 'Jijik', 'Netral'
    ]
    for emo in all_emotions:
        if emo in cross.columns:
            fig.add_trace(go.Bar(
                x=cross.index, y=cross[emo],
                name=emo, marker_color=EMOTION_COLORS.get(emo, '#64748B'),
            ))
    fig.update_layout(barmode='stack', **_base_layout(height=350))
    return fig


# ======================================================================
# 8. EMOJI ANALYSIS
# ======================================================================
def plot_emoji_analysis(df):
    all_emojis = []
    if 'emojis_str' in df.columns:
        for s in df['emojis_str'].dropna():
            if s:
                all_emojis.extend(str(s).split())
    elif 'emojis' in df.columns:
        for elist in df['emojis']:
            if isinstance(elist, list):
                all_emojis.extend(elist)

    if not all_emojis:
        return None, []

    counter = Counter(all_emojis).most_common(20)
    emojis = [e[0] for e in counter]
    counts = [e[1] for e in counter]

    fig = go.Figure(data=[go.Bar(
        x=emojis, y=counts,
        marker_color=COLORS['accent_blue'],
        text=counts, textposition='outside',
        textfont=dict(size=14),
    )])

    layout = _base_layout(height=300)
    layout['xaxis'] = dict(showgrid=False, color=COLORS['text_secondary'], tickfont=dict(size=20))
    fig.update_layout(**layout)
    return fig, counter


# ======================================================================
# 9. TOP ISU EXTRACTION
# ======================================================================
def extract_top_issues(df, top_n=15):
    from collections import Counter

    all_terms = []
    for text in df['cleaned_content'].dropna():
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        all_terms.extend([w for w in words if w not in STOPWORDS_ID])

    counter = Counter(all_terms).most_common(top_n)
    if not counter:
        return None

    terms = [c[0] for c in counter]
    freqs = [c[1] for c in counter]

    fig = go.Figure(data=[go.Bar(
        y=terms[::-1], x=freqs[::-1],
        orientation='h',
        marker_color=COLORS['accent_blue'],
        text=freqs[::-1], textposition='outside',
    )])

    fig.update_layout(**_base_layout(height=max(300, top_n * 28)))
    return fig


# ======================================================================
# 10. CROSS-PLATFORM ISSUE DIFFUSION
# ======================================================================
def plot_crossplatform_diffusion(df, top_n=8):
    from collections import Counter

    # Get top terms
    all_terms = []
    for text in df['cleaned_content'].dropna():
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        all_terms.extend([w for w in words if w not in STOPWORDS_ID])
    top_terms = [t[0] for t in Counter(all_terms).most_common(top_n)]

    if not top_terms:
        return None

    platforms = sorted(df['platform'].unique())
    data_matrix = []

    for term in top_terms:
        row = []
        for plat in platforms:
            sub = df[df['platform'] == plat]
            count = sub['cleaned_content'].str.lower().str.contains(term, na=False).sum()
            row.append(count)
        data_matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=data_matrix,
        x=platforms,
        y=top_terms,
        colorscale='Viridis',
        text=data_matrix,
        texttemplate='%{text}',
        textfont=dict(size=11, color='white'),
    ))

    fig.update_layout(**_base_layout(height=max(300, top_n * 40)))
    return fig


# ======================================================================
# 11. TOP INFLUENCERS PER PLATFORM
# ======================================================================
def get_top_influencers(df, platform, top_n=10, sort_by='total_engagement'):
    sub = df[df['platform'] == platform]
    if len(sub) == 0:
        return pd.DataFrame()

    influencers = sub.groupby('author').agg(
        total_posts=('cleaned_content', 'count'),
        total_engagement=('total_engagement', 'sum'),
        total_likes=('likes', 'sum'),
        total_views=('views', 'sum'),
        total_reach=('reach', 'sum'),
        dominant_sentiment=('sentiment_name', lambda x: x.mode().iloc[0] if len(x) > 0 else 'Netral'),
    ).reset_index()

    influencers = influencers.sort_values(sort_by, ascending=False).head(top_n)
    return influencers


def plot_top_influencers(df, platform, top_n=10):
    influencers = get_top_influencers(df, platform, top_n)
    if influencers.empty:
        return None

    colors = [COLORS.get(s, COLORS['Netral']) for s in influencers['dominant_sentiment']]

    fig = go.Figure(data=[go.Bar(
        y=influencers['author'].tolist()[::-1],
        x=influencers['total_engagement'].tolist()[::-1],
        orientation='h',
        marker_color=colors[::-1],
        text=[f"{v:,.0f}" for v in influencers['total_engagement'].tolist()[::-1]],
        textposition='outside',
    )])

    fig.update_layout(**_base_layout(height=max(300, top_n * 35)))
    return fig


# ======================================================================
# 12. TOP POSTS PER PLATFORM
# ======================================================================
def get_top_posts(df, platform, sort_col='total_engagement', top_n=5):
    platform_sort_map = {
        'Twitter': 'shares',
        'Facebook': 'likes',
        'Instagram': 'likes',
        'YouTube': 'views',
        'TikTok': 'views',
        'Threads': 'likes',
        'News': 'total_engagement',
    }
    col = platform_sort_map.get(platform, sort_col)
    sub = df[df['platform'] == platform].sort_values(col, ascending=False).head(top_n)
    return sub


# ======================================================================
# 13. NEWS SITE RANKING
# ======================================================================
def get_top_news_sites(df, top_n=15):
    news = df[df['platform'] == 'News'].copy()
    if len(news) == 0:
        return None

    import urllib.parse
    def extract_domain(url):
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain if domain else 'unknown'
        except:
            return 'unknown'

    news['domain'] = news['url'].apply(extract_domain)
    domain_counts = news['domain'].value_counts().head(top_n).reset_index()
    domain_counts.columns = ['Situs', 'Jumlah Berita']

    fig = go.Figure(data=[go.Bar(
        y=domain_counts['Situs'].tolist()[::-1],
        x=domain_counts['Jumlah Berita'].tolist()[::-1],
        orientation='h',
        marker_color=COLORS['accent_amber'],
        text=domain_counts['Jumlah Berita'].tolist()[::-1],
        textposition='outside',
    )])

    fig.update_layout(**_base_layout(height=max(300, top_n * 30)))
    return fig


# ======================================================================
# 14. HASHTAG & TERM ANALYSIS
# ======================================================================
def get_top_hashtags(df, top_n=20):
    all_tags = []
    for text in df['raw_content'].dropna():
        tags = re.findall(r'#(\w+)', text)
        all_tags.extend([t.lower() for t in tags if t.lower() not in STOPWORDS_ID])

    counter = Counter(all_tags).most_common(top_n)
    if not counter:
        return None, []

    tags = ['#' + c[0] for c in counter]
    freqs = [c[1] for c in counter]

    fig = go.Figure(data=[go.Bar(
        y=tags[::-1], x=freqs[::-1],
        orientation='h',
        marker=dict(color=freqs[::-1], colorscale='Plasma'),
        text=freqs[::-1], textposition='outside',
    )])

    fig.update_layout(**_base_layout(height=max(300, top_n * 28)))
    return fig, counter


def get_top_terms(df, top_n=20):
    all_terms = []
    for text in df['cleaned_content'].dropna():
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        all_terms.extend([w for w in words if w not in STOPWORDS_ID])

    counter = Counter(all_terms).most_common(top_n)
    if not counter:
        return None, []

    terms = [c[0] for c in counter]
    freqs = [c[1] for c in counter]

    fig = go.Figure(data=[go.Bar(
        y=terms[::-1], x=freqs[::-1],
        orientation='h',
        marker=dict(color=freqs[::-1], colorscale='Viridis'),
        text=freqs[::-1], textposition='outside',
    )])

    fig.update_layout(**_base_layout(height=max(300, top_n * 28)))
    return fig, counter


# ======================================================================
# 15. WORD CLOUDS (Dual: Frequency vs Reach)
# ======================================================================
def generate_wordcloud_base64(df, by='frequency', colormap='coolwarm'):
    if by == 'reach':
        high_reach = df[df['reach'] > df['reach'].median()]
        text_source = high_reach if len(high_reach) > 100 else df
        text = ' '.join(text_source['cleaned_content'].dropna().tolist()[:5000])
        colormap = 'winter'
    elif by == 'hashtag':
        all_tags = []
        for t in df['raw_content'].dropna().tolist()[:5000]:
            all_tags.extend(re.findall(r'#(\w+)', t))
        text = ' '.join([t.lower() for t in all_tags if t.lower() not in STOPWORDS_ID])
        colormap = 'plasma'
    else:
        text = ' '.join(df['cleaned_content'].dropna().tolist()[:5000])

    if not text.strip():
        text = 'sekolah rakyat pendidikan makan bergizi koperasi indonesia'

    wc = WordCloud(
        width=800, height=400,
        background_color=COLORS['bg_dark'],
        colormap=colormap,
        stopwords=STOPWORDS_ID,
        max_words=100,
        font_path=None,
        prefer_horizontal=0.7,
        min_font_size=8,
    ).generate(text)

    img = io.BytesIO()
    wc.to_image().save(img, format='PNG')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()


# ======================================================================
# 16. SENTIMENT TIMELINE PER PLATFORM
# ======================================================================
def plot_sentiment_timeline_platform(df, platform):
    sub = df[df['platform'] == platform]
    daily = sub.groupby(['date_str', 'sentiment_name']).size().unstack(fill_value=0).reset_index()
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily = daily.sort_values('date')

    fig = go.Figure()
    for sent, color in [('Positif', COLORS['Positif']), ('Netral', COLORS['Netral']), ('Negatif', COLORS['Negatif'])]:
        if sent in daily.columns:
            fig.add_trace(go.Scatter(
                x=daily['date'], y=daily[sent],
                name=sent, mode='lines',
                line=dict(color=color, width=2),
                fill='tonexty' if sent != 'Positif' else None,
            ))

    fig.update_layout(**_base_layout(height=280))
    return fig
