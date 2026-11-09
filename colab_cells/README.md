# 🕸️ Modul Scraping & Crawling Multi-Platform

Folder ini memuat seluruh mesin scraping dan crawler data publik untuk 3 topik fokus kebijakan:
1. **MBG (Makan Bergizi Gratis)**
2. **KDMP (Koperasi Desa Merah Putih)**
3. **Sekolah Rakyat**

Semua hasil scraping otomatis disimpan ke: `../ScrapeData/`

---

## 🚀 Cara Menjalankan Scraper

### Cara 1: Menggunakan Master Controller dari Root (Paling Mudah)
Buka terminal di root project (`d:\Project_Streamlit\IndoBERT_SNA_MT_PP`):
```bash
python run_scraper.py youtube     # Scraping YouTube
python run_scraper.py news        # Scraping Berita Online (Bing/Google/DDG)
python run_scraper.py tiktok      # Scraping TikTok
python run_scraper.py instagram   # Scraping Instagram
python run_scraper.py twitter     # Scraping Twitter/X
python run_scraper.py threads     # Scraping Threads
python run_scraper.py facebook    # Scraping Facebook
python run_scraper.py all         # Menjalankan seluruh platform secara berurutan
```

### Cara 2: Menjalankan Script Platform Langsung
```bash
python colab_cells/run_youtube_only.py
python colab_cells/run_news_only.py
python colab_cells/run_tiktok_only.py
python colab_cells/run_instagram_only.py
python colab_cells/run_twitter_only.py
python colab_cells/run_threads_only.py
python colab_cells/run_facebook_only.py
```

---

## ⚙️ Konfigurasi Kredensial & Keyword
* **[`cell_02_config.py`](file:///d:/Project_Streamlit/IndoBERT_SNA_MT_PP/colab_cells/cell_02_config.py)**:
  * File sentral yang memuat API Keys, cookies peramban (Twitter, TikTok, Instagram, Facebook), serta **139 variasi kata kunci pencarian**.
  * Jika cookie kadaluarsa, cukup perbarui nilainya di file ini atau di `.env`.
