# IndoBERT & SNA Intelligence Dashboard - Kementerian Pekerjaan Umum RI (Kemen PU)

Sistem analitik sentimen berbasis **Deep Learning IndoBERT (3-Kelas Sentimen & 9-Emosi)** dan **Social Network Analysis (SNA by Sentiment & Emotion)** untuk pemantauan opini publik, kebijakan infrastruktur, serta kepemimpinan di lingkungan **Kementerian Pekerjaan Umum Republik Indonesia (Kemen PU RI)**.

---

## 🔐 Kredensial & Akses Login Sistem

Aplikasi ini dilindungi oleh gerbang autentikasi berbasis sesi (Session State) dan enkripsi hash SHA-256. Tersedia 3 akun kedinasan bawaan untuk keperluan evaluasi dan demonstrasi:

| Peran Pengguna | ID / Username | Kata Sandi | Deskripsi Hak Akses |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin` | `kemenpu2026` | Akses menyeluruh: Laporan Harian, Dashboard SNA, Cockpit AI, Evaluasi |
| **Pimpinan** | `pimpinan` | `pu2026` | Akses Eksekutif: Slide Deck Laporan Harian & Ringkasan Kebijakan |
| **Tim Analis** | `analis` | `analis2026` | Akses Analitik Multiplatform, Dinamika Emosi & SNA |

*(Catatan: Anda juga dapat menggunakan tombol **Akses Cepat / Quick Login** pada layar login untuk masuk secara instan).*

---

## 🎯 1. Objek & Topik Penelitian

Project ini difokuskan pada 2 pilar topik utama:
1. **`Kementerian_PU`**:
   - **Nama Resmi**: Kementerian Pekerjaan Umum Republik Indonesia / Kementerian Pekerjaan Umum (Kemen PU RI / KemenPU).
   - **Fokus Kajian**: Kebijakan kelembagaan, proyek infrastruktur nasional (jalan tol, preservasi jalan nasional, jembatan, bendungan, tanggul sungai, irigasi, drainase penanganan banjir, air minum/SPAM, sanitasi Cipta Karya, IKN, dan Ditjen Bina Marga / SDA / Cipta Karya / Bina Konstruksi).
2. **`Menteri_PU`**:
   - **Nama Resmi / Tokoh**: Menteri Pekerjaan Umum / Menteri PU (Ir. Dody Hanggodo, M.P.E.) dan Wakil Menteri PU (Diana Kusumastuti).
   - **Fokus Kajian**: Kepemimpinan, sidak lapangan, kunjungan kerja, arahan/instruksi menteri, rapat kerja dengan Komisi V DPR RI, pernyataan pers, dan respons kebijakan terhadap aspirasi publik.

---

## 🌐 2. Multi-Platform Web Scraping (7 Kanal)

Scraper telah disiapkan di folder `colab_cells/` dengan target kuota dan integrasi 117 variasi kata kunci:
- **YouTube**: YouTube Data API v3 resmi + fallback `scrapetube`.
- **Berita Online (News)**: Google News RSS + Bing News RSS (Bebas rate-limit, multi-portal nasional).
- **Twitter / X**: Undetected ChromeDriver, filter cutoff, dan deduplikasi URL.
- **TikTok**: Modern layout interceptor + extractor DOM/JSON.
- **Instagram**: Multi-source caption (JSON-LD + GraphQL + DOM) dengan hashtag mapping PU.
- **Threads**: DOM text extractor, anti-throttling.
- **Facebook**: Undetected ChromeDriver dengan pengenalan entitas akun dan interaksi.

### Cara Menjalankan Scraper via Controller Sentral:
```bash
# Jalankan per platform spesifik:
python run_scraper.py news
python run_scraper.py youtube
python run_scraper.py twitter
python run_scraper.py tiktok
python run_scraper.py instagram
python run_scraper.py threads
python run_scraper.py facebook

# Gabungkan & bersihkan data dari semua platform (NLP Cleaning & Relevansi Topik):
python run_scraper.py combine

# Jalankan semua platform bertahap secara otomatis:
python run_scraper.py all
```

---

## 🧹 3. Pembersihan & Standarisasi Dataset

Eksekusi pembersihan dijalankan melalui `colab_cells/run_combine_all.py` yang menerapkan:
1. **Deduplikasi URL Global**: URL unik sebagai Primary Key.
2. **Two-Tiered Topic Filtering**:
   - *Core Regex & Co-occurrence*: Memvalidasi keberadaan entitas Kementerian PU & Menteri PU.
   - *Fatal Noise Elimination*: Menghapus spam judi, porn, crypto, gaming (PUBG), otomotif non-infrastruktur.
   - *Context Noise Filtering*: Mencegah noise kata "pu" biasa (puding, pupuk, puasa, kupu-kupu).
3. **Pembersihan Teks NLP**: Decoding entitas HTML, pembuangan URL dalam teks, reduksi huruf berulang (*character elongation*), normalisasi spasi.
4. **Output Dataset**:
   - `ScrapeData/FINAL_ALL_DATA.csv`: Dataset lengkap bersih master.
   - `data/master_scraped_corpus.csv`: Dataset siap inferensi machine learning & SNA.

---

## 🤖 4. Model IndoBERT & Pipeline Ekstraksi SNA

### A. Inferensi Lokal (CPU / GPU PC):
Jalankan satu perintah untuk memproses seluruh data korpus, menghasilkan prediksi sentimen, 9 emosi, serta graf SNA:
```bash
python run_pipeline_local.py
```
Hasil yang dihasilkan:
- `data/enriched_corpus_for_sna.parquet` & `.csv`: Dataset teranotasi lengkap.
- `data/all_topics_sna_by_sentiment.gexf` & `summary.json`: Graf SNA gabungan seluruh topik.
- `data/kementerian_pu_sna_by_sentiment.gexf` & `summary.json`: Graf SNA khusus Kementerian PU.
- `data/menteri_pu_sna_by_sentiment.gexf` & `summary.json`: Graf SNA khusus Menteri PU.

### B. Training / Fine-Tuning di Google Colab (GPU T4):
Buka file notebook:
`IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb`
Fitur notebook:
- Multi-key rotation Gemini Annotation untuk gold-standard training data.
- Fine-tuning IndoBERT Base 3-Class Sentiment.
- Fine-tuning IndoBERT Extended Plutchik 9-Class Emotion.
- Multi-layer SNA Generator (@mention layer & co-keyword layer).

---

## 📊 5. Menjalankan Dashboard Streamlit

Untuk membuka dashboard eksekutif interaktif:
1. Klik ganda file:
   `run_dashboard.bat`
2. Atau jalankan via terminal:
   ```bash
   python -m streamlit run app.py
   ```
Dashboard akan otomatis terbuka di browser pada alamat `http://localhost:8501`.

### Fitur Utama Dashboard:
- **Format Laporan Harian**: 21 Slide Deck standar pemantauan intelijen media Kementerian Pekerjaan Umum.
- **Dashboard Analisis Multi Platform**: 30 Halaman eksekutif analitik performa volume, reach, dan engagement 7 kanal.
- **Cockpit Analisis & Evaluasi Model**: Metrik akurasi, Macro F1, Confusion Matrix, dan SNA Interaktif (Pyvis & ekspor Gephi `.gexf`).

