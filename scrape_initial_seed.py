import os
import sys
import pandas as pd

# Add colab_cells to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'colab_cells'))

from colab_cells.cell_02_config import TOPICS, OUTPUT_DIR, detect_topic
from colab_cells.cell_06_news import scrape_news
from colab_cells.cell_03_youtube import scrape_youtube

print("=" * 70)
print("🚀 SCRAPING SEED DATA (NEWS & YOUTUBE) UNTUK KEMEN PU & MENTERI PU")
print("=" * 70)

news_results = []
yt_results = []

# Gunakan persis 5 keywords per topik dari cell_02_config.py
seed_keywords = TOPICS

# 1. SCRAPE NEWS
print("\n--- 1. Mengambil Berita Real-Time (Google News & Bing News) ---")
for topic, kws in seed_keywords.items():
    print(f"\n[Topik: {topic}]")
    for kw in kws:
        print(f"  • Scraping News: '{kw}'...")
        try:
            articles = scrape_news(kw, max_results=25)
            for a in articles:
                full_text = f"{a.get('content', '')} {a.get('description', '')}"
                t = detect_topic(full_text) or topic
                a['topic'] = t
                news_results.append(a)
            print(f"    -> Dapat {len(articles)} artikel")
        except Exception as e:
            print(f"    -> Gagal: {e}")

df_news = pd.DataFrame(news_results)
if not df_news.empty and 'url' in df_news.columns:
    df_news.drop_duplicates(subset=['url'], inplace=True)
    news_out = os.path.join(OUTPUT_DIR, "scraped_News_Only.csv")
    df_news.to_csv(news_out, index=False, encoding='utf-8-sig')
    print(f"\n✅ Tersimpan {len(df_news):,} artikel berita bersih di: {news_out}")

# 2. SCRAPE YOUTUBE
print("\n--- 2. Mengambil Video Real-Time (YouTube Data API v3) ---")
for topic, kws in seed_keywords.items():
    print(f"\n[Topik: {topic}]")
    for kw in kws[:4]:
        print(f"  • Scraping YouTube: '{kw}'...")
        try:
            videos = scrape_youtube(kw, max_results=15)
            for v in videos:
                full_text = f"{v.get('content', '')} {v.get('description', '')}"
                t = detect_topic(full_text) or topic
                v['topic'] = t
                yt_results.append(v)
            print(f"    -> Dapat {len(videos)} video")
        except Exception as e:
            print(f"    -> Gagal: {e}")

df_yt = pd.DataFrame(yt_results)
if not df_yt.empty and 'url' in df_yt.columns:
    df_yt.drop_duplicates(subset=['url'], inplace=True)
    yt_out = os.path.join(OUTPUT_DIR, "scraped_YouTube_Only.csv")
    df_yt.to_csv(yt_out, index=False, encoding='utf-8-sig')
    print(f"\n✅ Tersimpan {len(df_yt):,} video YouTube bersih di: {yt_out}")

print("\n" + "=" * 70)
print(f"🎉 SEED SCRAPING SELESAI!")
print(f"Total News    : {len(df_news) if not df_news.empty else 0:,} baris")
print(f"Total YouTube : {len(df_yt) if not df_yt.empty else 0:,} baris")
print("=" * 70)

