import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "db_kemenpu_sna")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Encode password if contains special characters
from urllib.parse import quote_plus
encoded_password = quote_plus(DB_PASSWORD)

DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_engine = None

def get_db_engine():
    """Mengembalikan SQLAlchemy engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URI, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _engine

def test_db_connection() -> dict:
    """Menguji status koneksi ke database PostgreSQL."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            count = conn.execute(text("SELECT count(*) FROM public_sentiment_posts;")).scalar()
            return {
                "status": "connected",
                "version": result,
                "total_records": count,
                "database": DB_NAME
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def get_posts_from_db(topic: str = None, platform: str = None, limit: int = 1000) -> pd.DataFrame:
    """Mengambil data sentimen dari PostgreSQL dengan filter opsional."""
    engine = get_db_engine()
    query = "SELECT * FROM public_sentiment_posts WHERE 1=1"
    params = {}
    
    if topic and topic != "Semua":
        query += " AND topic = :topic"
        params["topic"] = topic
    if platform and platform != "Semua":
        query += " AND platform = :platform"
        params["platform"] = platform
        
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    return df

def get_db_kpi_summary() -> dict:
    """Menghitung ringkasan statistik metrik dari PostgreSQL."""
    engine = get_db_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM public_sentiment_posts;")).scalar() or 0
        pos = conn.execute(text("SELECT COUNT(*) FROM public_sentiment_posts WHERE sentiment_name ILIKE '%positif%';")).scalar() or 0
        neg = conn.execute(text("SELECT COUNT(*) FROM public_sentiment_posts WHERE sentiment_name ILIKE '%negatif%';")).scalar() or 0
        net = conn.execute(text("SELECT COUNT(*) FROM public_sentiment_posts WHERE sentiment_name ILIKE '%netral%';")).scalar() or 0
        platforms = conn.execute(text("SELECT platform, COUNT(*) FROM public_sentiment_posts GROUP BY platform ORDER BY 2 DESC;")).fetchall()
        
    return {
        "total_posts": total,
        "positive": pos,
        "negative": neg,
        "neutral": net,
        "by_platform": dict(platforms)
    }

if __name__ == "__main__":
    res = test_db_connection()
    print("Database Connection Test:", res)
