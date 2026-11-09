"""
Dataset Preparation & Preprocessing Pipeline for IndoBERT Sentiment Analysis
Tugas Akhir: SNA & Sentimen Analisis Kebijakan Publik (MBG, KDMP, Sekolah Rakyat)
"""

import os
import sys
import re
import html
import pandas as pd

# Set standard output encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'ScrapeData')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILES = {
    'Facebook':  'scraped_Facebook_Only.csv',
    'Instagram': 'scraped_Instagram_Only.csv',
    'News':      'scraped_News_Only.csv',
    'Threads':   'scraped_Threads_Only.csv',
    'TikTok':    'scraped_TikTok_Only.csv',
    'Twitter':   'scraped_Twitter_Only.csv',
    'YouTube':   'scraped_YouTube_Only.csv',
}

def clean_text_for_bert(text):
    """
    Preprocessing Khusus Arsitektur Transformer (IndoBERT):
    - Membersihkan URL, Mention, Karakter kontrol, dan HTML entities.
    - TIDAK melakukan stemming atau pembuangan stopwords agar grammar & konteks negasi tetap utuh.
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # 1. Unescape HTML entities (&amp; -> &, &quot; -> ", dll)
    t = html.unescape(text)
    
    # 2. Hapus URL/Link (http, https, www)
    t = re.sub(r'https?://\S+|www\.\S+', '', t)
    
    # 3. Hapus mention (@username)
    t = re.sub(r'@[\w\.-]+', '', t)
    
    # 4. Bersihkan hashtag symbol tapi pertahankan teksnya (#SekolahRakyat -> SekolahRakyat)
    t = re.sub(r'#(\w+)', r'\1', t)
    
    # 5. Normalisasi spasi dan karakter whitespace berlebih
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    
    # 6. Hapus karakter non-printable / control characters
    t = "".join(ch for ch in t if ch.isprintable())
    
    return t.strip()

def consolidate_all_platforms():
    """
    Menggabungkan seluruh 7 file CSV scraping menjadi 1 Master Corpus.
    """
    print("=" * 75)
    print("🚀 MEMULAI KONSOLIDASI DATASET LINTAS 7 PLATFORM UNTUK INDOBERT & SNA")
    print("=" * 75)
    
    consolidated_records = []
    
    for platform, fname in CSV_FILES.items():
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"[WARN] File {fname} tidak ditemukan, dilewati.")
            continue
        
        try:
            df = pd.read_csv(fpath, low_memory=False)
            print(f"[{platform:10}] Membaca {len(df):>7,} baris dari {fname}...")
            
            # Ekstraksi field standar
            for _, row in df.iterrows():
                # Teks konten
                raw_content = str(row.get('content', ''))
                if raw_content.strip() == '' or raw_content.lower() == 'nan':
                    raw_content = str(row.get('description', ''))
                
                cleaned_content = clean_text_for_bert(raw_content)
                if len(cleaned_content.split()) < 3: # Minimal 3 kata
                    continue
                
                # Tanggal
                created_at = row.get('created_at', '')
                if pd.isna(created_at) or str(created_at).strip() == '':
                    created_at = row.get('scraped_at', '')
                
                # Interaksi
                likes = int(row.get('likes', 0) if pd.notna(row.get('likes')) else 0)
                comments = int(row.get('comments', 0) if pd.notna(row.get('comments')) else 0)
                shares = int(row.get('shares', 0) if pd.notna(row.get('shares')) else 0)
                reposts = int(row.get('reposts', 0) if pd.notna(row.get('reposts')) else 0)
                views = int(row.get('views', 0) if pd.notna(row.get('views')) else 0)
                
                total_engagement = likes + comments + shares + reposts
                
                # Author / Handle
                author = str(row.get('author', '')) if pd.notna(row.get('author')) else ''
                handle = str(row.get('handle', '')) if pd.notna(row.get('handle')) else ''
                user_id = handle if handle.strip() else author
                if not user_id.strip():
                    user_id = f"{platform}_User"
                
                consolidated_records.append({
                    'platform': platform,
                    'topic': str(row.get('topic', 'General')),
                    'keyword': str(row.get('keyword', '')),
                    'user_id': user_id,
                    'author': author,
                    'handle': handle,
                    'url': str(row.get('url', '')),
                    'raw_content': raw_content,
                    'cleaned_content': cleaned_content,
                    'created_at': created_at,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'reposts': reposts,
                    'views': views,
                    'total_engagement': total_engagement
                })
        except Exception as e:
            print(f"[ERROR] Gagal memproses {fname}: {e}")
            
    df_all = pd.DataFrame(consolidated_records)
    print(f"\nTotal Data Tergabung: {len(df_all):,} baris")
    
    # Deduplikasi Berbasis URL sebagai Primary Key (Sesuai instruksi: teks mirip dari URL berbeda tetap di-keep)
    before_dedup = len(df_all)
    url_clean = df_all['url'].fillna('').astype(str).str.strip()
    has_url = (url_clean != '') & (url_clean.str.lower() != 'nan')
    df_url = df_all[has_url].drop_duplicates(subset=['url'], keep='first')
    df_no_url = df_all[~has_url].drop_duplicates(subset=['cleaned_content'], keep='first')
    df_all = pd.concat([df_url, df_no_url], ignore_index=True)
    dedup_removed = before_dedup - len(df_all)
    print(f"Dihapus duplikat URL: {dedup_removed:,} baris (Teks serupa dari URL berbeda tetap dipertahankan)")
    print(f"Total Master Dataset Bersih: {len(df_all):,} baris")
    
    master_path = os.path.join(OUTPUT_DIR, 'master_scraped_corpus.csv')
    df_all.to_csv(master_path, index=False, encoding='utf-8-sig')
    print(f"💾 Tersimpan ke: {master_path}")
    
    return df_all

if __name__ == '__main__':
    consolidate_all_platforms()
