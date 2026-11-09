"""
================================================================================
🚀 END-TO-END LOCAL PIPELINE: INDOBERT INFERENCE & SNA GENERATOR
================================================================================
Menjalankan inferensi Deep Learning IndoBERT (Sentimen 3-Kelas & 9-Emosi)
serta membangun Graf Analisis Jaringan Sosial (SNA by Sentiment & Emotion)
untuk Kementerian Pekerjaan Umum (Kemen PU RI) & Menteri PU.
================================================================================
"""

import os
import sys
import json
import re
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.utils.data import Dataset, DataLoader
import networkx as nx

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
SNA_OUT_DIR = os.path.join(BASE_DIR, 'sna', 'output')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SNA_OUT_DIR, exist_ok=True)

MASTER_PATH = os.path.join(DATA_DIR, 'master_scraped_corpus.csv')
ENRICHED_PQ = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')
ENRICHED_CSV = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.csv')

SENT_MODEL_DIR = os.path.join(MODELS_DIR, 'best_indobert_sentiment')
if not os.path.exists(SENT_MODEL_DIR):
    SENT_MODEL_DIR = os.path.join(MODELS_DIR, 'best_indobert_sentiment_v2')

EMO_MODEL_DIR = os.path.join(MODELS_DIR, 'best_indobert_emotion')

SENT_LABEL_MAP = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}

# Load metadata emosi jika ada
EMO_LABEL_MAP = {
    0: 'Kemarahan', 1: 'Antisipasi', 2: 'Kejijikan', 3: 'Ketakutan',
    4: 'Kegembiraan', 5: 'Kesedihan', 6: 'Keterkejutan', 7: 'Kepercayaan', 8: 'Netral'
}
emo_meta_path = os.path.join(DATA_DIR, 'emotion_9_metadata.json')
if os.path.exists(emo_meta_path):
    try:
        with open(emo_meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            if 'idx_to_label' in meta:
                EMO_LABEL_MAP = {int(k): v for k, v in meta['idx_to_label'].items()}
    except Exception:
        pass

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class TextInferenceDataset(Dataset):
    def __init__(self, texts):
        self.texts = [str(t) if pd.notna(t) else "" for t in texts]

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        return self.texts[idx]

def run_indobert_sentiment_inference(df, batch_size=64, max_len=128):
    print("\n" + "=" * 65)
    print("🤖 1. INFERENSI INDOBERT V2 (3-KELAS SENTIMEN)")
    print("=" * 65)
    print(f"Model Checkpoint: {SENT_MODEL_DIR}")
    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(SENT_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(SENT_MODEL_DIR).to(device)
    model.eval()

    texts = df['cleaned_content'].fillna(df['raw_content']).tolist()
    dataset = TextInferenceDataset(texts)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_preds = []
    all_scores = []
    total_batches = len(loader)

    with torch.no_grad():
        for step, batch in enumerate(loader):
            encoded = tokenizer(
                list(batch),
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors='pt'
            ).to(device)

            logits = model(**encoded).logits
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            preds = np.argmax(probs, axis=1)
            
            # Continuous score: P(Positif) - P(Negatif) [-1.0, 1.0]
            scores = probs[:, 2] - probs[:, 0]
            all_preds.extend(preds)
            all_scores.extend(scores)

            if (step + 1) % 25 == 0 or (step + 1) == total_batches:
                print(f"  Batch {step + 1}/{total_batches} selesai...")

    df['sentiment_label'] = all_preds
    df['predicted_sentiment'] = [SENT_LABEL_MAP.get(p, 'Netral') for p in all_preds]
    df['sentiment_name'] = df['predicted_sentiment']
    df['sentiment_score'] = all_scores
    return df

def run_indobert_emotion_inference(df, batch_size=64, max_len=128):
    print("\n" + "=" * 65)
    print("🎭 2. INFERENSI INDOBERT 9-EMOSI (PLUTCHIK EXTENDED)")
    print("=" * 65)
    print(f"Model Checkpoint: {EMO_MODEL_DIR}")
    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(EMO_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(EMO_MODEL_DIR).to(device)
    model.eval()

    texts = df['cleaned_content'].fillna(df['raw_content']).tolist()
    dataset = TextInferenceDataset(texts)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_emo_preds = []
    total_batches = len(loader)

    with torch.no_grad():
        for step, batch in enumerate(loader):
            encoded = tokenizer(
                list(batch),
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors='pt'
            ).to(device)

            logits = model(**encoded).logits
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_emo_preds.extend(preds)

            if (step + 1) % 25 == 0 or (step + 1) == total_batches:
                print(f"  Batch {step + 1}/{total_batches} selesai...")

    df['emotion_label'] = all_emo_preds
    df['emotion'] = [EMO_LABEL_MAP.get(e, 'Netral') for e in all_emo_preds]
    return df

# ==============================================================================
# 3. BUILD SNA GRAPH BY SENTIMENT & EMOTION
# ==============================================================================
mention_pattern = re.compile(r'@([A-Za-z0-9_\.]{2,30})')

def normalize_handle(h):
    if not h or str(h).lower() in ['nan', 'none', 'anonim', '']:
        return None
    h = str(h).strip().lower()
    h = h.lstrip('@')
    h = re.sub(r'\s+', '_', h)
    return h if len(h) >= 2 else None

def build_and_export_sna(df_corpus, topic_name='All_Topics', min_edge_weight=1):
    print(f"\n--- Membangun Graf SNA Topik: {topic_name} ---")
    if topic_name != 'All_Topics':
        df_sub = df_corpus[df_corpus['topic'].astype(str).str.lower() == topic_name.lower()].copy()
    else:
        df_sub = df_corpus.copy()

    print(f"Total baris diproses: {len(df_sub):,} entri")
    if df_sub.empty:
        print(f"[WARN] Data untuk {topic_name} kosong. Skip SNA.")
        return None

    G = nx.DiGraph()
    author_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    author_emotions = defaultdict(lambda: defaultdict(int))
    author_platforms = {}
    author_engagements = defaultdict(int)
    author_post_count = defaultdict(int)

    target_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    target_emotions = defaultdict(lambda: defaultdict(int))
    edges_dict = defaultdict(lambda: {'weight': 0, 'sentiments': [], 'emotions': [], 'types': []})

    keyword_authors = defaultdict(list)
    mention_edge_count = 0

    for _, row in df_sub.iterrows():
        author_raw = str(row.get('author', row.get('user_id', '')))
        handle_raw = str(row.get('handle', ''))
        author = normalize_handle(handle_raw) or normalize_handle(author_raw)
        if not author:
            continue

        sent = str(row.get('predicted_sentiment', 'Netral'))
        emo = str(row.get('emotion', 'Netral'))
        plat = str(row.get('platform', 'SocialMedia'))
        eng = int(row.get('total_engagement', 0) or 0)
        kw = str(row.get('keyword', ''))

        author_sentiments[author][sent] += 1
        author_emotions[author][emo] += 1
        author_platforms[author] = plat
        author_engagements[author] += eng
        author_post_count[author] += 1

        if kw and kw.lower() not in ['nan', 'none', '']:
            keyword_authors[kw].append((author, sent, emo))

        # Layer 1: @mentions
        raw_text = str(row.get('raw_content', ''))
        mentions = mention_pattern.findall(raw_text)
        for m in mentions:
            target = normalize_handle(m)
            if target and target != author and len(target) >= 2:
                target_sentiments[target][sent] += 1
                target_emotions[target][emo] += 1
                edge_key = (author, target)
                edges_dict[edge_key]['weight'] += 1
                edges_dict[edge_key]['sentiments'].append(sent)
                edges_dict[edge_key]['emotions'].append(emo)
                edges_dict[edge_key]['types'].append('mention')
                mention_edge_count += 1

    # Layer 2: Co-keyword
    co_keyword_count = 0
    for kw, authors_list in keyword_authors.items():
        unique_authors = list(set(a[0] for a in authors_list))
        if len(unique_authors) < 2 or len(unique_authors) > 300:
            continue

        author_freq = Counter(a[0] for a in authors_list)
        top_authors = [a for a, _ in author_freq.most_common(15)]

        for i in range(len(top_authors)):
            for j in range(i + 1, len(top_authors)):
                u1, u2 = top_authors[i], top_authors[j]
                edge_key = tuple(sorted([u1, u2]))
                edges_dict[edge_key]['weight'] += 1
                edges_dict[edge_key]['sentiments'].append('Netral')
                edges_dict[edge_key]['emotions'].append('Netral')
                edges_dict[edge_key]['types'].append('co_keyword')
                co_keyword_count += 1

    # Add Nodes
    all_users = set(author_sentiments.keys()) | set(target_sentiments.keys())
    for (src, tgt) in edges_dict.keys():
        all_users.add(src)
        all_users.add(tgt)

    for u in all_users:
        s_counts = author_sentiments[u] if sum(author_sentiments[u].values()) > 0 else target_sentiments[u]
        dom_sent = max(s_counts, key=s_counts.get) if s_counts else 'Netral'

        e_counts = author_emotions[u] if sum(author_emotions[u].values()) > 0 else target_emotions[u]
        dom_emo = max(e_counts, key=e_counts.get) if e_counts else 'Netral'

        pos_cnt = s_counts.get('Positif', 0)
        neg_cnt = s_counts.get('Negatif', 0)
        tot_cnt = sum(s_counts.values())
        actor_nss = round(((pos_cnt - neg_cnt) / tot_cnt * 100), 2) if tot_cnt > 0 else 0.0

        G.add_node(
            u,
            label=u,
            sentiment=dom_sent,
            emotion=dom_emo,
            nss=actor_nss,
            platform=author_platforms.get(u, 'Mentioned'),
            total_engagement=author_engagements.get(u, 0),
            post_count=author_post_count.get(u, 0)
        )

    # Add Edges
    for (src, tgt), edata in edges_dict.items():
        if edata['weight'] >= min_edge_weight:
            most_sent = Counter(edata['sentiments']).most_common(1)[0][0]
            most_emo = Counter(edata['emotions']).most_common(1)[0][0]
            edge_type = Counter(edata['types']).most_common(1)[0][0]
            G.add_edge(src, tgt, weight=edata['weight'], sentiment=most_sent,
                       emotion=most_emo, edge_type=edge_type)

    print(f"  Graf SNA Berhasil: {G.number_of_nodes():,} Nodes, {G.number_of_edges():,} Edges")

    # Hitung Sentralitas
    in_deg = dict(G.in_degree(weight='weight'))
    out_deg = dict(G.out_degree(weight='weight'))
    nx.set_node_attributes(G, in_deg, 'in_degree')
    nx.set_node_attributes(G, out_deg, 'out_degree')

    if G.number_of_edges() > 0 and G.number_of_nodes() <= 30000:
        try:
            bc = nx.betweenness_centrality(G, weight='weight', k=min(300, G.number_of_nodes()))
            nx.set_node_attributes(G, bc, 'betweenness')
        except Exception:
            pass

    # Top Influencers
    combined_score = {}
    for u in G.nodes():
        nd = G.nodes[u]
        combined_score[u] = in_deg.get(u, 0) * 10 + nd.get('total_engagement', 0) * 0.001 + nd.get('post_count', 0)

    top_inf = sorted(combined_score.items(), key=lambda x: x[1], reverse=True)[:20]
    top_summary = []
    for rank, (u, score) in enumerate(top_inf, 1):
        nd = G.nodes[u]
        top_summary.append({
            'rank': rank, 'user': u, 'in_degree': in_deg.get(u, 0),
            'out_degree': out_deg.get(u, 0), 'sentiment': nd['sentiment'],
            'emotion': nd['emotion'], 'nss': nd['nss'],
            'platform': nd['platform'], 'engagement': nd['total_engagement'],
            'post_count': nd.get('post_count', 0), 'composite_score': round(score, 2)
        })

    prefix = topic_name.lower().replace(' ', '_')
    gexf_file = os.path.join(DATA_DIR, f"{prefix}_sna_by_sentiment.gexf")
    json_file = os.path.join(DATA_DIR, f"{prefix}_sna_summary.json")

    # Simpan juga ke sna/output
    gexf_sna_out = os.path.join(SNA_OUT_DIR, f"{prefix}_sna_by_sentiment.gexf")
    json_sna_out = os.path.join(SNA_OUT_DIR, f"{prefix}_sna_summary.json")

    try:
        nx.write_gexf(G, gexf_file)
        nx.write_gexf(G, gexf_sna_out)
    except Exception as e:
        print(f"[WARN] GEXF export error: {e}")

    with open(json_file, 'w', encoding='utf-8') as fj:
        json.dump({
            'topic': topic_name, 'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(), 'top_influencers': top_summary,
            'edge_layers': {
                'mention_edges': mention_edge_count,
                'co_keyword_edges': co_keyword_count
            }
        }, fj, indent=2, ensure_ascii=False)

    with open(json_sna_out, 'w', encoding='utf-8') as fj:
        json.dump({
            'topic': topic_name, 'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(), 'top_influencers': top_summary,
            'edge_layers': {
                'mention_edges': mention_edge_count,
                'co_keyword_edges': co_keyword_count
            }
        }, fj, indent=2, ensure_ascii=False)

    print(f"  ✅ Gephi GEXF : {gexf_file}")
    print(f"  ✅ Summary JSON: {json_file}")
    return G

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    print("=" * 75)
    print("🚀 MEMULAI PIPELINE PEMROSESAN DATA KEMENTERIAN PEKERJAAN UMUM RI")
    print("=" * 75)

    # 1. Cek / Jalankan combine jika master belum ada atau dipanggil langsung
    if not os.path.exists(MASTER_PATH):
        print("[INFO] master_scraped_corpus.csv belum ada. Menjalankan run_combine_all.py...")
        from colab_cells import run_combine_all
    
    if not os.path.exists(MASTER_PATH):
        print(f"[ERROR] {MASTER_PATH} tetap tidak ditemukan. Pastikan ada data hasil scraping di ScrapeData/.")
        sys.exit(1)

    df_master = pd.read_csv(MASTER_PATH, low_memory=False)
    print(f"Total Baris Master Corpus: {len(df_master):,} entri")

    # 2. IndoBERT Sentiment Inference
    df_enriched = run_indobert_sentiment_inference(df_master)

    # 3. IndoBERT Emotion Inference
    df_enriched = run_indobert_emotion_inference(df_enriched)

    # 4. Simpan Parquet & CSV
    print(f"\n💾 Menyimpan Corpus Ter-Enrich...")
    df_enriched.to_parquet(ENRICHED_PQ, index=False)
    df_enriched.to_csv(ENRICHED_CSV, index=False, encoding='utf-8-sig')
    print(f"  • Parquet: {ENRICHED_PQ}")
    print(f"  • CSV    : {ENRICHED_CSV}")

    # 5. Bangun Graf SNA
    print("\n🕸️ 3. MEMBANGUN GRAF SNA (SOCIAL NETWORK ANALYSIS)")
    build_and_export_sna(df_enriched, 'All_Topics')
    build_and_export_sna(df_enriched, 'Kementerian_PU')
    build_and_export_sna(df_enriched, 'Menteri_PU')

    # 6. Ringkasan Eksekutif
    pos = (df_enriched['predicted_sentiment'] == 'Positif').sum()
    neg = (df_enriched['predicted_sentiment'] == 'Negatif').sum()
    net = (df_enriched['predicted_sentiment'] == 'Netral').sum()
    tot = len(df_enriched)
    nss = ((pos - neg) / tot) * 100 if tot > 0 else 0

    print("\n" + "=" * 75)
    print("📊 RINGKASAN EKSEKUTIF KEMENTERIAN PEKERJAAN UMUM:")
    print("=" * 75)
    print(f"Total Korpus Dianalisis : {tot:,} dokumen")
    print(f"• Sentimen Positif      : {pos:,} ({pos/tot*100:.1f}%)")
    print(f"• Sentimen Netral       : {net:,} ({net/tot*100:.1f}%)")
    print(f"• Sentimen Negatif      : {neg:,} ({neg/tot*100:.1f}%)")
    print(f"• Net Sentiment Score   : {nss:+.1f} poin")
    print("=" * 75)
    print("🎉 SELURUH PIPELINE SELESAI DENGAN SUKSES! Siap Ditampilkan di Streamlit Dashboard.")
    print("=" * 75)

if __name__ == '__main__':
    main()

