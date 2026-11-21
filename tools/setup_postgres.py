import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_PASS = "Aghnasyarief#1795"
DB_NAME = "db_kemenpu_sna"

def setup():
    try:
        # 1. Connect to default postgres database
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password=DB_PASS,
            host="localhost",
            port=5432
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version_info = cursor.fetchone()[0]
        print("==================================================")
        print("KONEKSI POSTGRESQL BERHASIL!")
        print(f"Versi Engine: {version_info}")
        print("==================================================")
        
        # 2. Check if db_kemenpu_sna exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s;", (DB_NAME,))
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE {DB_NAME};')
            print(f"Database '{DB_NAME}' berhasil dibuat!")
        else:
            print(f"Database '{DB_NAME}' sudah ada.")
            
        cursor.close()
        conn.close()

        # 3. Connect to the new database and create tables
        conn_app = psycopg2.connect(
            dbname=DB_NAME,
            user="postgres",
            password=DB_PASS,
            host="localhost",
            port=5432
        )
        conn_app.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_app = conn_app.cursor()

        # Tabel 1: Posts & Analisis Sentimen IndoBERT
        cur_app.execute("""
        CREATE TABLE IF NOT EXISTS public_sentiment_posts (
            id SERIAL PRIMARY KEY,
            post_id VARCHAR(100) UNIQUE,
            platform VARCHAR(50) NOT NULL,
            author VARCHAR(150),
            created_at TIMESTAMP,
            topic VARCHAR(100),
            content TEXT NOT NULL,
            sentiment_name VARCHAR(20),
            sentiment_score FLOAT,
            emotion_name VARCHAR(50),
            emotion_score FLOAT,
            engagement_likes INT DEFAULT 0,
            engagement_comments INT DEFAULT 0,
            engagement_shares INT DEFAULT 0,
            post_url TEXT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Tabel 2: SNA Nodes (Aktor Jejaring)
        cur_app.execute("""
        CREATE TABLE IF NOT EXISTS sna_nodes (
            id SERIAL PRIMARY KEY,
            node_id VARCHAR(150) UNIQUE NOT NULL,
            label VARCHAR(150),
            platform VARCHAR(50),
            community_id INT,
            degree_centrality FLOAT,
            betweenness_centrality FLOAT,
            in_degree INT DEFAULT 0,
            out_degree INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Tabel 3: SNA Edges (Relasi Aktor Mention/Reply/Retweet)
        cur_app.execute("""
        CREATE TABLE IF NOT EXISTS sna_edges (
            id SERIAL PRIMARY KEY,
            source_node VARCHAR(150) NOT NULL,
            target_node VARCHAR(150) NOT NULL,
            relation_type VARCHAR(50) DEFAULT 'mention',
            weight FLOAT DEFAULT 1.0,
            platform VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_source FOREIGN KEY (source_node) REFERENCES sna_nodes(node_id) ON DELETE CASCADE,
            CONSTRAINT fk_target FOREIGN KEY (target_node) REFERENCES sna_nodes(node_id) ON DELETE CASCADE
        );
        """)

        # Tabel 4: Audit Log Ingestion (Riwayat Penarikan Data)
        cur_app.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_logs (
            id SERIAL PRIMARY KEY,
            run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            platform VARCHAR(50),
            start_date DATE,
            end_date DATE,
            records_fetched INT,
            records_processed INT,
            status VARCHAR(30),
            notes TEXT
        );
        """)

        print("Semua skema tabel berhasil dibuat:")
        print("1. public_sentiment_posts (Data teks & prediksi IndoBERT)")
        print("2. sna_nodes (Aktor & metrik sentralitas SNA)")
        print("3. sna_edges (Relasi antar-aktor)")
        print("4. ingestion_logs (Log audit riwayat penarikan harian)")
        print("==================================================")

        cur_app.close()
        conn_app.close()
        return True
    except Exception as e:
        print("GAGAL:", e)
        return False

if __name__ == "__main__":
    setup()
