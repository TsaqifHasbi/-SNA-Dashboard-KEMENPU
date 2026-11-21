import sys
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.db_manager import get_db_engine

def migrate():
    parquet_path = root_dir / 'data' / 'enriched_corpus_for_sna.parquet'
    if not parquet_path.exists():
        print("Berkas data/enriched_corpus_for_sna.parquet tidak ditemukan!")
        return
        
    print(f"Membaca berkas {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    total_rows = len(df)
    print(f"Total baris ditemukan: {total_rows:,} baris.")

    # Mapping kolom dari parquet ke tabel PostgreSQL
    # Tabel target: public_sentiment_posts
    # Kolom: post_id, platform, author, created_at, topic, content, sentiment_name, sentiment_score, emotion_name, emotion_score, engagement_likes, engagement_comments, engagement_shares, post_url
    
    df_db = pd.DataFrame()
    # Generate unique post_id
    urls = df['url'].tolist()
    post_ids = []
    for i, u in enumerate(urls):
        if pd.isna(u) or not str(u).strip():
            post_ids.append(f"post_idx_{i}")
        else:
            post_ids.append(f"{i}_{str(u)[:80]}")
    df_db['post_id'] = post_ids
    
    # Ambil index yang cocok
    valid_idx = df_db.index
    df_sub = df.loc[valid_idx]
    
    df_db['platform'] = df_sub['platform'].fillna('Unknown')
    df_db['author'] = df_sub['author'].fillna(df_sub.get('handle', '-')).astype(str).str[:150]
    df_db['created_at'] = pd.to_datetime(df_sub['date'], errors='coerce')
    df_db['topic'] = df_sub['topic'].fillna('Semua')
    df_db['content'] = df_sub['cleaned_content'].fillna(df_sub.get('raw_content', ''))
    df_db['sentiment_name'] = df_sub['sentiment_name'].fillna('Netral')
    df_db['sentiment_score'] = df_sub['sentiment_score'].fillna(0.0).astype(float)
    df_db['emotion_name'] = df_sub['emotion'].fillna('Netral')
    df_db['emotion_score'] = df_sub['emotion_confidence'].fillna(0.0).astype(float)
    df_db['engagement_likes'] = df_sub['likes'].fillna(0).astype(int)
    df_db['engagement_comments'] = df_sub['comments'].fillna(0).astype(int)
    df_db['engagement_shares'] = df_sub['shares'].fillna(0).astype(int)
    df_db['post_url'] = df_sub['url'].fillna('').astype(str)

    engine = get_db_engine()
    print("Membersihkan data lama dan memulai migrasi batch ke PostgreSQL table 'public_sentiment_posts'...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE public_sentiment_posts RESTART IDENTITY CASCADE;"))
    
    # Simpan via to_sql chunksize 2000
    df_db.to_sql(
        'public_sentiment_posts',
        con=engine,
        if_exists='append',
        index=False,
        chunksize=2000,
        method='multi'
    )
    
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM public_sentiment_posts;")).scalar()
        print(f"MIGRASI SUKSES! Total data di PostgreSQL sekarang: {count:,} baris.")

if __name__ == "__main__":
    migrate()
