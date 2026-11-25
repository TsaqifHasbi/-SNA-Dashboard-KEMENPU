import os
import re
import sys
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.sentiment_corrector import correct_sentiment, align_emotion_valence_9class
from src.tab_sentiment_drilldown import extract_affected_region, extract_issue_category
from src.data_loader import detect_emotion
from models.execute_all_platforms_filter import canonicalize_url

PARQUET_PATH = root_dir / 'data' / 'enriched_corpus_for_sna.parquet'
CSV_PATH = root_dir / 'data' / 'enriched_corpus_for_sna.csv'
MASTER_CSV_PATH = root_dir / 'data' / 'master_scraped_corpus.csv'

SENTIMENT_MODEL_DIR = (
    root_dir / 'models' / 'best_indobert_sentiment_v2'
    if (root_dir / 'models' / 'best_indobert_sentiment_v2' / 'config.json').exists()
    else root_dir / 'models' / 'best_indobert_sentiment'
)
EMOTION_MODEL_DIR = root_dir / 'models' / 'best_indobert_emotion'

SENTIMENT_LABEL_MAP = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}
EMOTION_LABEL_MAP = {
    0: 'Trust', 1: 'Anticipation', 2: 'Joy',
    3: 'Disgust', 4: 'Fear', 5: 'Sadness',
    6: 'Anger', 7: 'Surprise', 8: 'Neutral'
}
EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral'
}

WIB_TZ = datetime.timezone(datetime.timedelta(hours=7))


def _decode_tiktok_snowflake(url: str):
    """Ekstrak timestamp WIB presisi detik dari 64-bit snowflake ID pada URL TikTok."""
    m = re.search(r'tiktok\.com/[^/]+/(?:video|photo)/(\d{15,21})', str(url or ''))
    if not m:
        return None
    try:
        ts = int(m.group(1)) >> 32
        dt_wib = datetime.datetime.fromtimestamp(ts, WIB_TZ).replace(tzinfo=None)
        if 2016 <= dt_wib.year <= 2027:
            return pd.Timestamp(dt_wib)
    except Exception:
        pass
    return None


def _parse_relative_time(s: str, ref_dt: pd.Timestamp):
    """Konversi string relatif seperti '5h ago', '2d ago', '11mo ago', '3y ago'."""
    m = re.match(r'^(\d+)\s*(s|sec|second|m|min|minute|h|hr|hour|d|day|w|wk|week|mo|month|y|yr|year)s?\s*ago$', s, re.IGNORECASE)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith('s'):
        return ref_dt - pd.Timedelta(seconds=val)
    if unit in ('m', 'min', 'minute'):
        return ref_dt - pd.Timedelta(minutes=val)
    if unit.startswith('h'):
        return ref_dt - pd.Timedelta(hours=val)
    if unit.startswith('d'):
        return ref_dt - pd.Timedelta(days=val)
    if unit.startswith('w'):
        return ref_dt - pd.Timedelta(weeks=val)
    if unit in ('mo', 'month'):
        return ref_dt - pd.Timedelta(days=val * 30)
    if unit.startswith('y'):
        return ref_dt - pd.Timedelta(days=val * 365)
    return None


def parse_created_at_smart(c_at, url='', old_dt=None, ref_dt=None):
    """
    Parser tanggal tangguh lintas platform (WIB/WITA/WIT/ISO/TikTok Snowflake/M-D/Relative).
    - Selalu memprioritaskan tanggal eksplisit di created_at agar tanggal korup otomatis sembuh.
    - Menjamin tahun berada pada rentang valid [2005, 2027].
    """
    if ref_dt is None:
        ref_dt = pd.Timestamp.now()

    s = str(c_at).strip() if pd.notna(c_at) else ''

    # 1. Cek format eksplisit YYYY-MM-DD atau YYYY-M-D (dengan atau tanpa WIB/WITA/WIT/ISO)
    if s and s.lower() not in ('nan', 'none', 'nat', ''):
        cleaned = re.sub(r'\s+(?:WIB|WITA|WIT|UTC|GMT)\b', '', s, flags=re.IGNORECASE).strip()

        # ISO / standard YYYY-MM-DD...
        m_ymd = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?)?', cleaned)
        if m_ymd:
            yr, mo, dy = int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))
            hr = int(m_ymd.group(4)) if m_ymd.group(4) else 0
            mn = int(m_ymd.group(5)) if m_ymd.group(5) else 0
            sc = int(m_ymd.group(6)) if m_ymd.group(6) else 0
            if 2005 <= yr <= 2027:
                try:
                    dt = pd.Timestamp(year=yr, month=mo, day=dy, hour=hr, minute=mn, second=sc)
                    # Jika sumber asli ISO UTC ('Z' atau '+00:00'), konversi ke WIB (+7 jam)
                    if s.endswith('Z') or '+00:00' in s:
                        dt = dt + pd.Timedelta(hours=7)
                    return dt
                except Exception:
                    pass

        # 2. Untuk TikTok (M-D atau relative seperti '5h ago', '9-28'), dekode snowflake URL dulu!
        if 'tiktok.com' in str(url or '').lower():
            tt_dt = _decode_tiktok_snowflake(url)
            if tt_dt is not None:
                return tt_dt

        # 3. Format M-D non-snowflake (fallback tahun berjalan/sebelumnya)
        m_md = re.match(r'^(\d{1,2})-(\d{1,2})$', cleaned)
        if m_md:
            mo, dy = int(m_md.group(1)), int(m_md.group(2))
            yr = ref_dt.year if (mo, dy) <= (ref_dt.month, ref_dt.day) else ref_dt.year - 1
            try:
                return pd.Timestamp(year=yr, month=mo, day=dy)
            except Exception:
                pass

        # 4. Format relatif ('2d ago', '3y ago', dll)
        # Jika sudah ada old_dt yang valid (dan bukan fallback bug hari ini saat old_dt = dummy), pertahankan old_dt
        rel_dt = _parse_relative_time(cleaned, ref_dt)
        if rel_dt is not None:
            if old_dt is not None and pd.notna(old_dt):
                try:
                    odt = pd.Timestamp(old_dt)
                    if getattr(odt, 'tzinfo', None) is not None:
                        odt = odt.tz_localize(None)
                    if 2005 <= odt.year <= 2027 and odt.date() != ref_dt.date():
                        return odt
                except Exception:
                    pass
            return rel_dt

        # 5. Fallback general pd.to_datetime setelah strip WIB
        dt = pd.to_datetime(cleaned, errors='coerce')
        if pd.notna(dt):
            if getattr(dt, 'tzinfo', None) is not None:
                dt = dt.tz_convert('Asia/Jakarta').tz_localize(None)
            if 2005 <= dt.year <= 2027:
                return dt

    # 6. Coba TikTok snowflake bila created_at kosong
    if 'tiktok.com' in str(url or '').lower():
        tt_dt = _decode_tiktok_snowflake(url)
        if tt_dt is not None:
            return tt_dt

    # 7. Fallback old_dt bila valid
    if old_dt is not None and pd.notna(old_dt):
        try:
            odt = pd.Timestamp(old_dt)
            if getattr(odt, 'tzinfo', None) is not None:
                odt = odt.tz_localize(None)
            if 2005 <= odt.year <= 2027:
                return odt
        except Exception:
            pass

    return pd.NaT


def run_indobert_inference_subset(texts, batch_size=64, max_length=128):
    """
    Menjalankan inferensi IndoBERT Sentimen (v2) dan IndoBERT 9-Emosi pada baris baru/belum terinferensi.
    Mengembalikan tuple: (sent_preds, sent_scores, emo_preds, emo_confs)
    """
    n = len(texts)
    if n == 0:
        return [], [], [], []

    sent_preds = ['Netral'] * n
    sent_scores = [0.0] * n
    emo_preds = [detect_emotion(t) for t in texts]
    emo_confs = [0.80] * n

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 1. IndoBERT Sentiment v2
        if (SENTIMENT_MODEL_DIR / 'config.json').exists():
            print(f"   🤖 Memuat IndoBERT Sentimen ({SENTIMENT_MODEL_DIR.name}) di {device} untuk {n:,} baris baru...")
            tok_s = AutoTokenizer.from_pretrained(str(SENTIMENT_MODEL_DIR))
            mod_s = AutoModelForSequenceClassification.from_pretrained(str(SENTIMENT_MODEL_DIR)).to(device)
            mod_s.eval()

            sp, sc = [], []
            with torch.no_grad():
                for i in range(0, n, batch_size):
                    batch = [str(x)[:1000] for x in texts[i:i + batch_size]]
                    enc = tok_s(batch, truncation=True, padding=True, max_length=max_length, return_tensors='pt').to(device)
                    probs = torch.softmax(mod_s(**enc).logits, dim=1).cpu().numpy()
                    preds = np.argmax(probs, axis=1)
                    pol = probs[:, 2] - probs[:, 0]  # Kontinu [-1.0, +1.0]
                    sp.extend(SENTIMENT_LABEL_MAP[int(p)] for p in preds)
                    sc.extend(float(v) for v in pol)
                    if ((i // batch_size) + 1) % 10 == 0 or (i + batch_size) >= n:
                        print(f"      Sentimen batch {min(i + batch_size, n):,}/{n:,} selesai...")
            sent_preds, sent_scores = sp, sc
            del mod_s, tok_s

        # 2. IndoBERT 9-Class Emotion
        if (EMOTION_MODEL_DIR / 'config.json').exists():
            print(f"   🎭 Memuat IndoBERT 9-Emosi ({EMOTION_MODEL_DIR.name}) di {device} untuk {n:,} baris baru...")
            tok_e = AutoTokenizer.from_pretrained(str(EMOTION_MODEL_DIR))
            mod_e = AutoModelForSequenceClassification.from_pretrained(str(EMOTION_MODEL_DIR)).to(device)
            mod_e.eval()

            ep, ec = [], []
            with torch.no_grad():
                for i in range(0, n, batch_size):
                    batch = [str(x)[:1000] for x in texts[i:i + batch_size]]
                    enc = tok_e(batch, truncation=True, padding=True, max_length=max_length, return_tensors='pt').to(device)
                    probs = torch.softmax(mod_e(**enc).logits, dim=1).cpu().numpy()
                    preds = np.argmax(probs, axis=1)
                    confs = np.max(probs, axis=1)
                    ep.extend(EMOTION_LABEL_MAP.get(int(p), 'Neutral') for p in preds)
                    ec.extend(float(c) for c in confs)
                    if ((i // batch_size) + 1) % 10 == 0 or (i + batch_size) >= n:
                        print(f"      Emosi batch {min(i + batch_size, n):,}/{n:,} selesai...")
            emo_preds, emo_confs = ep, ec
            del mod_e, tok_e

    except Exception as e:
        print(f"   [WARN] Inferensi IndoBERT gagal ({e}), menggunakan fallback rule-based...")

    return sent_preds, sent_scores, emo_preds, emo_confs


def main():
    print(f"1. Membaca Master Scraped Corpus: {MASTER_CSV_PATH}")
    df_master = pd.read_csv(MASTER_CSV_PATH, low_memory=False)
    print(f"   Total baris master (awal): {len(df_master):,}")

    # Pastikan URL kanonik & bebas duplikat URL / token Google News kembar
    if 'url' in df_master.columns:
        df_master['url'] = df_master['url'].apply(canonicalize_url)
        before_dedup = len(df_master)
        has_u = df_master['url'] != ''
        df_master = pd.concat([
            df_master[has_u].drop_duplicates(subset=['url'], keep='first'),
            df_master[~has_u]
        ], ignore_index=True)
        news_m = (df_master.get('platform', '') == 'News')
        if news_m.any():
            df_nw = df_master[news_m].copy()
            df_nw['_is_gn'] = df_nw['url'].astype(str).str.contains('news.google.com/', case=False, na=False).astype(int)
            df_nw['_orig_idx'] = df_nw.index
            df_nw_sorted = df_nw.sort_values(['_is_gn', '_orig_idx'])
            nw_dups = df_nw_sorted.duplicated(subset=['author', 'cleaned_content'], keep='first')
            if nw_dups.any():
                df_master = df_master.drop(df_nw_sorted[nw_dups].index).reset_index(drop=True)
        if len(df_master) < before_dedup:
            print(f"   [DEDUP] Dihapus {before_dedup - len(df_master):,} duplikat URL kanonik -> Sisa bersih: {len(df_master):,} baris")

    old_lookup = {}
    if PARQUET_PATH.exists():
        print(f"2. Membaca Parquet lama untuk mewarisi skor & emosi terlatih...")
        df_old = pd.read_parquet(PARQUET_PATH)
        print(f"   Total baris parquet lama: {len(df_old):,}")
        for _, row in df_old.iterrows():
            u_raw = str(row.get('url', '')).strip()
            u_can = canonicalize_url(u_raw)
            sc_raw = row.get('sentiment_score', np.nan)
            # Pulihkan label IndoBERT murni (sebelum koreksi rule-based lama) dari raw_indobert_sentiment atau sentiment_score
            raw_ib = row.get('raw_indobert_sentiment', None)
            if not raw_ib or pd.isna(raw_ib):
                if pd.notna(sc_raw):
                    fv = float(sc_raw)
                    raw_ib = 'Positif' if fv >= 0.35 else ('Negatif' if fv <= -0.35 else 'Netral')
                else:
                    raw_ib = row.get('predicted_sentiment', 'Netral')
            entry_meta = {
                'sentiment_score': sc_raw,
                'raw_indobert_sentiment': str(raw_ib),
                'emotion': row.get('emotion', 'Neutral'),
                'emotion_confidence': row.get('emotion_confidence', np.nan),
                'date': row.get('date', None),
            }
            if u_raw and u_raw not in old_lookup:
                old_lookup[u_raw] = entry_meta
            if u_can and u_can not in old_lookup:
                old_lookup[u_can] = entry_meta
    else:
        print("2. Parquet lama belum ada — semua baris akan diinferensi penuh.")

    print("3. Memetakan metadata lama, memparsing tanggal lintas-platform, & mendeteksi baris baru...")
    ref_now = pd.Timestamp.now()
    n_rows = len(df_master)

    s_scores = [0.0] * n_rows
    s_preds = ['Netral'] * n_rows
    emos = ['Neutral'] * n_rows
    emo_confs = [0.80] * n_rows
    dates = [pd.NaT] * n_rows

    infer_indices = []
    infer_texts = []

    texts_series = df_master['cleaned_content'].fillna(df_master.get('raw_content', '')).astype(str)

    for idx, (_, row) in enumerate(df_master.iterrows()):
        u = str(row.get('url', '')).strip()
        c_at = row.get('created_at', None)
        meta = old_lookup.get(u)

        # Selalu parsing tanggal secara cerdas dari created_at + URL TikTok snowflake
        old_dt = meta['date'] if meta else None
        dt = parse_created_at_smart(c_at, url=u, old_dt=old_dt, ref_dt=ref_now)
        dates[idx] = dt

        # Deteksi apakah baris ini sudah punya inferensi IndoBERT asli atau masih sentinel dummy (0.85 / 0.80)
        needs_infer = True
        if meta is not None:
            sc_val = meta['sentiment_score']
            ec_val = meta['emotion_confidence']
            is_dummy_sentinel = (
                pd.notna(sc_val) and pd.notna(ec_val)
                and abs(float(sc_val) - 0.85) < 1e-6
                and abs(float(ec_val) - 0.80) < 1e-6
            )
            if pd.notna(sc_val) and not is_dummy_sentinel:
                needs_infer = False
                s_scores[idx] = float(sc_val)
                s_preds[idx] = str(meta['raw_indobert_sentiment'])
                emos[idx] = str(meta['emotion'])
                emo_confs[idx] = float(ec_val) if pd.notna(ec_val) else 0.85

        if needs_infer:
            infer_indices.append(idx)
            infer_texts.append(texts_series.iloc[idx])

    print(f"   • Mewarisi inferensi IndoBERT lama : {n_rows - len(infer_indices):,} baris")
    print(f"   • Baris baru perlu IndoBERT        : {len(infer_indices):,} baris")

    if infer_indices:
        sp, sc, ep, ec = run_indobert_inference_subset(infer_texts, batch_size=64, max_length=128)
        for pos, row_idx in enumerate(infer_indices):
            s_preds[row_idx] = sp[pos]
            s_scores[row_idx] = sc[pos]
            emos[row_idx] = ep[pos]
            emo_confs[row_idx] = ec[pos]

    df_master['sentiment_score'] = np.array(s_scores, dtype='float64')
    df_master['raw_indobert_sentiment'] = s_preds
    df_master['predicted_sentiment'] = s_preds
    df_master['emotion'] = emos
    df_master['emotion_confidence'] = np.array(emo_confs, dtype='float64')
    df_master['date'] = pd.to_datetime(dates, errors='coerce')

    # Isi jika masih ada NaT langka dengan median tanggal valid
    nat_count = int(df_master['date'].isna().sum())
    if nat_count > 0:
        med_dt = df_master['date'].dropna().median()
        print(f"   [INFO] Mengisi {nat_count} baris tanpa tanggal valid dengan median ({med_dt.strftime('%Y-%m-%d')}).")
        df_master['date'] = df_master['date'].fillna(med_dt)

    df_master['date_str'] = df_master['date'].dt.strftime('%Y-%m-%d')
    df_master['year_month'] = df_master['date'].dt.strftime('%Y-%m')

    print("4. Menjalankan Koreksi Sentimen Termutakhir (Whitelist Fasilitas/Perpus, Anti-Sarkasme CAPS & Netralisasi ESDM)...")
    final_sents = []
    for t, s, sc in zip(texts_series, df_master['predicted_sentiment'], df_master['sentiment_score']):
        cs, _, _, _ = correct_sentiment(str(t), str(s), float(sc) if pd.notna(sc) else 0.0)
        final_sents.append(cs)

    df_master['sentiment_name'] = final_sents
    df_master['predicted_sentiment'] = final_sents
    df_master['sentiment_label'] = df_master['sentiment_name'].map({'Negatif': 0, 'Netral': 1, 'Positif': 2}).fillna(1).astype('int8')

    print("5. Menyelaraskan Valensi Emosi 9-Kelas Plutchik...")
    aligned_emos = []
    for t, s, e in zip(texts_series, df_master['sentiment_name'], df_master['emotion']):
        ae = align_emotion_valence_9class(str(t), str(s), str(e))
        aligned_emos.append(ae)

    df_master['emotion'] = aligned_emos
    df_master['emotion_sentiment'] = df_master['emotion'].map(EMOTION_TO_SENTIMENT).fillna('Netral')

    # Hitung reach & total_engagement
    for col in ['likes', 'comments', 'shares', 'reposts', 'views']:
        if col in df_master.columns:
            df_master[col] = pd.to_numeric(df_master[col], errors='coerce').fillna(0).astype('int64')
        else:
            df_master[col] = np.int64(0)

    df_master['total_engagement'] = (df_master['likes'] + df_master['comments'] + df_master['shares'] + df_master['reposts']).astype('int64')
    df_master['reach'] = (df_master['views'] + (df_master['likes'] * 3) + (df_master['comments'] * 5) + (df_master['shares'] * 10) + (df_master['reposts'] * 10)).astype('int64')

    print("6. Mengekstraksi Wilayah Terdampak & Kategori Isu...")
    df_master['detected_region'] = texts_series.apply(extract_affected_region)
    df_master['issue_category'] = texts_series.apply(extract_issue_category)

    print(f"7. Menyimpan berkas ke {PARQUET_PATH} dan {CSV_PATH}...")
    df_master.to_parquet(PARQUET_PATH, engine='pyarrow', index=False)
    print(f"✅ Berhasil menyimpan Parquet: {len(df_master):,} baris.")

    if CSV_PATH.exists():
        df_master.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        print(f"✅ Berhasil menyimpan CSV: {len(df_master):,} baris.")

    print("\n=== VERIFIKASI AKHIR INTEGRITAS TANGGAL ===")
    bad_year = (df_master['date'].dt.year < 2005).sum()
    print(f"Rentang date_str : {df_master['date_str'].min()} s.d. {df_master['date_str'].max()} (year<2005: {bad_year})")
    print("Distribusi 19 hari terakhir (Nov 05 - Nov 23):")
    nov_counts = df_master[df_master['date_str'] >= '2026-11-05']['date_str'].value_counts().sort_index()
    print(nov_counts.to_string())

    print("\n=== VERIFIKASI AKHIR DISTRIBUSI SENTIMEN ===")
    print(df_master['sentiment_name'].value_counts(dropna=False))

    print("\n=== DISTRIBUSI WILAYAH TERDAMPAK (TOP 10) ===")
    print(df_master['detected_region'].value_counts().head(10))


if __name__ == '__main__':
    main()
