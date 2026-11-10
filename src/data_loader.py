import os
import re
import pandas as pd
# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PARQUET_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')
CSV_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.csv')

# Indonesian Stopwords
STOPWORDS_ID = {
    'dan', 'yang', 'di', 'ini', 'itu', 'ke', 'dari', 'untuk', 'pada', 'dengan',
    'adalah', 'akan', 'atau', 'juga', 'dalam', 'bisa', 'ada', 'tidak', 'sudah',
    'karena', 'oleh', 'saat', 'para', 'seperti', 'lebih', 'harus', 'kami', 'kita',
    'bagi', 'saja', 'masih', 'tentang', 'telah', 'mereka', 'ia', 'itu', 'hal',
    'tersebut', 'kata', 'agar', 'lalu', 'maka', 'namun', 'serta', 'pun', 'yakni',
    'antara', 'setiap', 'tetapi', 'hingga', 'secara', 'begitu', 'bahwa', 'atas',
    'nya', 'se', 'tak', 'yg', 'gak', 'ga', 'gk', 'udah', 'dah', 'lah', 'dong',
    'kok', 'sih', 'kan', 'tuh', 'nih', 'deh', 'ya', 'lo', 'gue', 'lu', 'gw',
    'https', 'http', 'www', 'com', 'rt', 'amp', 'nan', 'none',
}

TOPIC_STOPWORDS = {
    'kemenpu', 'kementerian', 'pekerjaan', 'umum', 'menteri', 'pu',
    'kemenpupr', 'pupr', 'program', 'pemerintah', 'ri', 'indonesia'
}

ALL_STOPWORDS = STOPWORDS_ID | TOPIC_STOPWORDS

EMOTION_LEXICON = {
    'Senang': ['senang', 'bahagia', 'gembira', 'sukacita', 'ceria', 'riang', 'puas',
               'bangga', 'syukur', 'bersyukur', 'senyum', 'tertawa', 'hore', 'mantap',
               'keren', 'asik', 'asyik', 'hebat', 'luar biasa', 'amazing', 'good', 'love',
               'suka', 'yeay', 'yey', 'bravo', 'top', 'joss', 'mantul', 'wah'],
    'Sedih': ['sedih', 'duka', 'pilu', 'nelangsa', 'haru', 'menangis', 'nangis',
              'menyesal', 'kecewa', 'kehilangan', 'tragis', 'muram', 'galau', 'hopeless',
              'menderita', 'derita', 'kasihan', 'miris', 'pedih'],
    'Marah': ['marah', 'kesal', 'geram', 'murka', 'emosi', 'dongkol', 'jengkel',
              'benci', 'muak', 'berang', 'ngamuk', 'amarah', 'dendam', 'kutuk',
              'laknat', 'bangsat', 'brengsek', 'sialan', 'kampret', 'anjing', 'goblog',
              'bodoh', 'tolol', 'idiot', 'goblok', 'busuk', 'bajingan'],
    'Takut': ['takut', 'khawatir', 'cemas', 'was-was', 'ngeri', 'menakutkan', 'horor',
              'panik', 'gentar', 'gelisah', 'waswas', 'ragu', 'phobia', 'teror',
              'ancaman', 'mengancam', 'bahaya', 'berbahaya', 'waspada', 'seram'],
    'Terkejut': ['terkejut', 'kaget', 'heran', 'tercengang', 'terperangah', 'wow',
                 'astaga', 'astagfirullah', 'duh', 'waduh', 'gila', 'anjir', 'njir',
                 'shock', 'speechless', 'ternyata', 'mendadak', 'tiba-tiba'],
    'Jijik': ['jijik', 'mual', 'muak', 'basi', 'busuk', 'jorok', 'kotor', 'sampah',
              'kotoran', 'najis', 'hina', 'rendah', 'menjijikkan', 'ogah', 'eneg',
              'menjemukan', 'bosan', 'ilfeel'],
}

def detect_emotion(text):
    if not isinstance(text, str) or not text.strip():
        return 'Netral'
    text_lower = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_LEXICON.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[emotion] = score
    if not scores:
        return 'Netral'
    return max(scores, key=scores.get)

def extract_emojis(text):
    if not isinstance(text, str):
        return []
    # pyrefly: ignore[missing-import]
    import emoji
    return [c for c in text if c in emoji.EMOJI_DATA]

@st.cache_resource(show_spinner=False)
def _load_main_data_cached(file_mtime: float):
    if os.path.exists(PARQUET_PATH):
        try:
            df = pd.read_parquet(PARQUET_PATH, engine='pyarrow')
        except Exception:
            df = pd.read_parquet(PARQUET_PATH)
    elif os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, low_memory=False)
    else:
        raise FileNotFoundError(f"Data tidak ditemukan di {PARQUET_PATH} atau {CSV_PATH}")

    # Drop heavy unused columns early to minimize memory footprint on Streamlit Cloud
    unused_cols = ['thumbnail', 'duration', 'saves', 'views_text', 'description', 'scraped_at', 'post_type', 'source']
    df.drop(columns=[c for c in unused_cols if c in df.columns], inplace=True, errors='ignore')

    # Standardize textual columns & share string memory between raw_content and cleaned_content
    for col in ['cleaned_content', 'handle', 'url']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)

    if 'cleaned_content' in df.columns:
        if 'raw_content' not in df.columns:
            df['raw_content'] = df['cleaned_content']
        else:
            df['raw_content'] = df['cleaned_content']
    elif 'raw_content' in df.columns:
        df['raw_content'] = df['raw_content'].fillna('').astype(str)

    if 'author' in df.columns:
        df['author'] = df['author'].fillna(df.get('handle', '')).fillna('anonim').astype(str)

    # Deduplicate normalized URLs without duplicating dataframe memory
    if 'url' in df.columns:
        norm_url = df['url'].str.replace('/photo/', '/video/', regex=False)
        valid_url = norm_url.str.len() > 10
        dup_mask = valid_url & norm_url.duplicated(keep='first')
        if dup_mask.any():
            dup_indices = df.index[dup_mask]
            df.drop(index=dup_indices, inplace=True)
        del norm_url, valid_url, dup_mask

    # Downcast categorical columns to drastically reduce memory on Streamlit Cloud (saves ~40MB)
    if 'platform' in df.columns:
        df['platform'] = df['platform'].fillna('Other').astype(str)
    if 'topic' in df.columns:
        df['topic'] = df['topic'].fillna('Kementerian_PU').astype(str)

    # Clean outlier values and downcast numeric types to int32/int8
    for col in ['likes', 'comments', 'shares', 'reposts', 'views', 'total_engagement', 'reach']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).clip(lower=0, upper=500_000).astype('int32')
        else:
            df[col] = 0

    df['total_engagement'] = (df['likes'] + df['comments'] + df['shares'] + df['reposts']).astype('int32')
    df['reach'] = (df['views'] + (df['likes'] * 3) + (df['comments'] * 5) + (df['shares'] * 10) + (df['reposts'] * 10)).astype('int32')

    if 'sentiment_label' in df.columns:
        df['sentiment_label'] = pd.to_numeric(df['sentiment_label'], errors='coerce').fillna(1).astype('int8')
        label_map = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}
        if 'sentiment_name' not in df.columns:
            df['sentiment_name'] = df['sentiment_label'].map(label_map).fillna('Netral')

    if 'date' not in df.columns or df['date'].isna().all():
        df['date'] = pd.to_datetime(df['created_at'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')[0], errors='coerce')
        if df['date'].isna().sum() > 0:
            valid_median = df['date'].dropna().median()
            df['date'] = df['date'].fillna(valid_median)
            
    if 'date_str' not in df.columns:
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    if 'year_month' not in df.columns:
        df['year_month'] = df['date'].dt.to_period('M').astype(str)

    # Fail-safe valence alignment: Negative sentiments must never have Joy/Trust/Anticipation
    if 'emotion' in df.columns and 'sentiment_name' in df.columns:
        mismatched = (df['sentiment_name'] == 'Negatif') & (df['emotion'].isin(['Joy', 'Trust', 'Anticipation']))
        if mismatched.any():
            try:
                from src.sentiment_corrector import align_emotion_valence_9class
                df.loc[mismatched, 'emotion'] = [
                    align_emotion_valence_9class(t, s, e)
                    for t, s, e in zip(df.loc[mismatched, 'cleaned_content'], df.loc[mismatched, 'sentiment_name'], df.loc[mismatched, 'emotion'])
                ]
            except Exception:
                pass

    # Detect emotion only if missing (parquet already contains precomputed aligned emotions)
    if 'emotion' not in df.columns:
        df['emotion'] = df['cleaned_content'].apply(detect_emotion)
        try:
            from src.sentiment_corrector import align_emotion_valence_9class
            if 'sentiment_name' in df.columns:
                df['emotion'] = [
                    align_emotion_valence_9class(t, s, e)
                    for t, s, e in zip(df['cleaned_content'], df['sentiment_name'], df['emotion'])
                ]
        except Exception:
            pass

    # Downcast categorical columns to category to save ~200MB RAM on Streamlit Community Cloud
    cat_cols = ['platform', 'topic', 'sentiment_name', 'emotion', 'predicted_sentiment', 'emotion_sentiment']
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].fillna('Unknown').astype('category')

    import gc
    gc.collect()

    return df

def load_main_data():
    target_path = PARQUET_PATH if os.path.exists(PARQUET_PATH) else CSV_PATH
    mtime = os.path.getmtime(target_path) if os.path.exists(target_path) else 0.0
    return _load_main_data_cached(mtime)

def filter_dataset(df, selected_topic='Semua', selected_platform='Semua', start_date=None, end_date=None):
    mask = None

    if selected_topic and selected_topic != 'Semua':
        m = (df['topic'] == selected_topic)
        mask = m if mask is None else (mask & m)

    if selected_platform and selected_platform != 'Semua':
        m = (df['platform'] == selected_platform)
        mask = m if mask is None else (mask & m)

    if start_date and end_date:
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        m = (df['date'] >= start_ts) & (df['date'] <= end_ts)
        mask = m if mask is None else (mask & m)

    if mask is None:
        return df
    return df[mask]


# Cache reload trigger: 2026-11-07 Permanent Alignment 286k Corpus & Emotion-Valence Fix
