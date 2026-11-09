"""
Pipeline Eksekusi Lokal IndoBERT & SNA untuk Kementerian PU & Menteri PU
Menjalankan:
1. Inferensi Sentimen IndoBERT V2 (3 Kelas)
2. Inferensi 9 Emosi Plutchik (9 Kelas)
3. Enrichment Metrik Engagement, Reach, dan Normalisasi Tanggal
4. Pembangunan Graf Jaringan SNA Multilayer (Mention & Co-Keyword)
Output langsung disimpan ke folder data/ lokal tanpa ketergantungan cloud.
"""

import os
import sys
import time
import json
import re
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
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

MASTER_PATH = os.path.join(DATA_DIR, 'master_scraped_corpus.csv')
OUT_CSV = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.csv')
OUT_PQ = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')

SENT_DIR = os.path.join(MODELS_DIR, 'best_indobert_sentiment_v2')
EMO_DIR = os.path.join(MODELS_DIR, 'best_indobert_emotion')

EMOTION_9_CLASSES = [
    'Trust', 'Anticipation', 'Joy', 'Disgust', 'Fear',
    'Sadness', 'Anger', 'Surprise', 'Neutral'
]
EMOTION_TO_SENTIMENT = {
    'Trust': 'Positif', 'Anticipation': 'Positif', 'Joy': 'Positif',
    'Disgust': 'Negatif', 'Fear': 'Negatif', 'Sadness': 'Negatif', 'Anger': 'Negatif',
    'Surprise': 'Netral', 'Neutral': 'Netral'
}

def batch_predict(model, tokenizer, texts, device, batch_size=64, max_length=128, desc="Inferensi"):
    preds, probs = [], []
    total = len(texts)
    t0 = time.time()
    for i in range(0, total, batch_size):
        batch_texts = [str(t)[:400] for t in texts[i:i+batch_size]]
        enc = tokenizer(batch_texts, truncation=True, padding=True, max_length=max_length, return_tensors='pt').to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            pb = torch.softmax(logits, dim=1).cpu().numpy()
        preds.extend(np.argmax(pb, axis=1))
        probs.append(pb)
        
        done = min(i + batch_size, total)
        if (i // batch_size + 1) % 25 == 0 or done == total:
            elapsed = time.time() - t0
            speed = done / elapsed if elapsed > 0 else 0
            pct = (done / total) * 100
            print(f"  [{desc}] {done:,}/{total:,} ({pct:5.1f}%) | Kecepatan: {speed:5.1f} teks/detik | Sisa waktu: {(total-done)/speed if speed>0 else 0:4.0f}s", flush=True)
            
    return np.array(preds), np.vstack(probs)

def normalize_handle(h):
    if not h or str(h).lower() in ['nan', 'none', 'anonim', '']:
        return None
    h = str(h).strip().lower().lstrip('@')
    h = re.sub(r'\s+', '_', h)
    return h if len(h) >= 2 else None

def build_sna_graphs(df_corpus):
    print("\n" + "=" * 75)
    print("🕸️  MEMBANGUN GRAF SOCIAL NETWORK ANALYSIS (SNA) MULTILAYER")
    print("=" * 75)
    
    mention_pattern = re.compile(r'@([A-Za-z0-9_\.]{2,30})')
    
    def export_graph_for_topic(df_sub, topic_name):
        print(f"\n--- Memproses Graf SNA Topik: {topic_name} ({len(df_sub):,} entri) ---")
        G = nx.DiGraph()
        author_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
        author_emotions = defaultdict(lambda: defaultdict(int))
        author_platforms = {}
        author_engagements = defaultdict(int)
        author_post_count = defaultdict(int)

        target_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
        target_emotions = defaultdict(lambda: defaultdict(int))
        edges_dict = defaultdict(lambda: {'weight': 0, 'sentiments': [], 'emotions': [], 'types': []})
        
        mention_edge_count = 0
        keyword_authors = defaultdict(list)
        
        for _, row in df_sub.iterrows():
            author_raw = str(row.get('author', row.get('user_id', '')))
            handle_raw = str(row.get('handle', ''))
            author = normalize_handle(handle_raw) or normalize_handle(author_raw)
            if not author:
                continue

            sent = str(row.get('predicted_sentiment', 'Netral'))
            emo = str(row.get('emotion', 'Neutral'))
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

        print(f"  Layer 1 (@mention teks asli): {mention_edge_count:,} interaksi terdeteksi")

        # Layer 2: Co-keyword
        co_keyword_count = 0
        for kw, authors_list in keyword_authors.items():
            unique_authors = list(set(a[0] for a in authors_list))
            if len(unique_authors) < 2 or len(unique_authors) > 500:
                continue
            author_freq = Counter(a[0] for a in authors_list)
            top_authors = [a for a, _ in author_freq.most_common(20)]
            auth_sentiment_map = {a[0]: (a[1], a[2]) for a in authors_list}

            for i_idx in range(len(top_authors)):
                for j_idx in range(i_idx + 1, min(i_idx + 6, len(top_authors))):
                    a1, a2 = top_authors[i_idx], top_authors[j_idx]
                    ek = (min(a1, a2), max(a1, a2))
                    edges_dict[ek]['weight'] += 1
                    edges_dict[ek]['sentiments'].append(auth_sentiment_map.get(a1, ('Netral', 'Neutral'))[0])
                    edges_dict[ek]['emotions'].append(auth_sentiment_map.get(a1, ('Netral', 'Neutral'))[1])
                    edges_dict[ek]['types'].append('co_keyword')
                    co_keyword_count += 1

        print(f"  Layer 2 (Co-keyword topical): {co_keyword_count:,} interaksi terdeteksi")

        # Nodes
        all_actors = set(author_sentiments.keys()) | set(target_sentiments.keys())
        for u in all_actors:
            s_counts = author_sentiments[u] if sum(author_sentiments[u].values()) > 0 else target_sentiments[u]
            dom_sent = max(s_counts, key=s_counts.get) if s_counts else 'Netral'

            e_counts = author_emotions[u] if sum(author_emotions[u].values()) > 0 else target_emotions[u]
            dom_emo = max(e_counts, key=e_counts.get) if e_counts else 'Neutral'

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

        # Edges
        for (src, tgt), edata in edges_dict.items():
            if edata['weight'] >= 1:
                most_sent = Counter(edata['sentiments']).most_common(1)[0][0]
                most_emo = Counter(edata['emotions']).most_common(1)[0][0]
                edge_type = Counter(edata['types']).most_common(1)[0][0]
                G.add_edge(src, tgt, weight=edata['weight'], sentiment=most_sent,
                           emotion=most_emo, edge_type=edge_type)

        print(f"  Total Graf {topic_name}: {G.number_of_nodes():,} Nodes, {G.number_of_edges():,} Edges")

        # Centrality
        in_deg = dict(G.in_degree(weight='weight'))
        out_deg = dict(G.out_degree(weight='weight'))
        nx.set_node_attributes(G, in_deg, 'in_degree')
        nx.set_node_attributes(G, out_deg, 'out_degree')

        if G.number_of_edges() > 0 and G.number_of_nodes() <= 50000:
            try:
                bc = nx.betweenness_centrality(G, weight='weight', k=min(500, G.number_of_nodes()))
                nx.set_node_attributes(G, bc, 'betweenness')
            except Exception:
                pass

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

        nx.write_gexf(G, gexf_file)
        with open(json_file, 'w', encoding='utf-8') as fj:
            json.dump({
                'topic': topic_name, 'total_nodes': G.number_of_nodes(),
                'total_edges': G.number_of_edges(), 'top_influencers': top_summary,
                'edge_layers': {
                    'mention_edges': mention_edge_count,
                    'co_keyword_edges': co_keyword_count
                }
            }, fj, indent=2, ensure_ascii=False)

        print(f"  [EXPORT] Gephi GEXF -> {gexf_file}")
        print(f"  [EXPORT] Summary JSON -> {json_file}")

    # Export All Topics
    export_graph_for_topic(df_corpus, 'All_Topics')
    
    # Export per topic
    for t_name in ['Kementerian_PU', 'Menteri_PU']:
        sub = df_corpus[df_corpus['topic'].astype(str).str.lower() == t_name.lower()].copy()
        if len(sub) > 0:
            export_graph_for_topic(sub, t_name)

def main():
    print("=" * 75)
    print("🚀 PIPELINE INFERENSI LOKAL INDOBERT & GENERATOR SNA KEMEN PU")
    print("=" * 75)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Perangkat Komputasi: {device.type.upper()} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Multi-core CPU'})")
    
    if not os.path.exists(MASTER_PATH):
        raise FileNotFoundError(f"File {MASTER_PATH} tidak ditemukan!")
        
    print(f"Membaca data master: {MASTER_PATH}")
    df = pd.read_csv(MASTER_PATH, low_memory=False)
    print(f"Total baris data yang akan diproses: {len(df):,} baris")
    
    # 1. Inferensi Sentimen
    print("\n--- 1. Memuat Model IndoBERT Sentimen V2 ---")
    s_tok = AutoTokenizer.from_pretrained(SENT_DIR)
    s_mod = AutoModelForSequenceClassification.from_pretrained(SENT_DIR).to(device)
    s_mod.eval()
    
    print("Memulai Inferensi Sentimen (Negatif, Netral, Positif)...")
    sp, sprob = batch_predict(s_mod, s_tok, df['cleaned_content'].values, device, batch_size=64, desc="Sentimen")
    df['sentiment_label'] = sp
    df['predicted_sentiment'] = pd.Series(sp).map({0: 'Negatif', 1: 'Netral', 2: 'Positif'}).values
    df['sentiment_score'] = sprob[:, 2] - sprob[:, 0]
    df['sentiment_name'] = df['predicted_sentiment']
    
    # Free memory
    del s_mod
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    # 2. Inferensi 9 Emosi
    print("\n--- 2. Memuat Model IndoBERT 9 Emosi Plutchik ---")
    e_tok = AutoTokenizer.from_pretrained(EMO_DIR)
    e_mod = AutoModelForSequenceClassification.from_pretrained(EMO_DIR).to(device)
    e_mod.eval()
    
    print("Memulai Inferensi 9 Emosi Plutchik...")
    ep, eprob = batch_predict(e_mod, e_tok, df['cleaned_content'].values, device, batch_size=64, desc="9 Emosi ")
    df['emotion'] = pd.Series(ep).map({i: l for i, l in enumerate(EMOTION_9_CLASSES)}).values
    df['emotion_confidence'] = np.max(eprob, axis=1)
    df['emotion_sentiment'] = df['emotion'].map(EMOTION_TO_SENTIMENT)
    
    del e_mod
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 3. Metrik Tanggal & Engagement
    print("\n--- 3. Menghitung Metrik Analitik & Engagement ---")
    if 'date' not in df.columns or df['date'].isna().all():
        df['date'] = pd.to_datetime(df['created_at'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')[0], errors='coerce')
    df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df['year_month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)

    for c in ['likes', 'comments', 'shares', 'reposts', 'views']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).clip(0, 500000).astype(int)
        else:
            df[c] = 0

    df['total_engagement'] = df['likes'] + df['comments'] + df['shares'] + df['reposts']
    df['reach'] = df['views'] + (df['likes'] * 3) + (df['comments'] * 5) + (df['shares'] * 10) + (df['reposts'] * 10)

    # 4. Simpan ke CSV & Parquet
    print(f"\nMenyimpan hasil ke:")
    print(f"  -> {OUT_CSV}")
    print(f"  -> {OUT_PQ}")
    df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    df.to_parquet(OUT_PQ, index=False)
    
    # 5. Bangun Graf SNA
    build_sna_graphs(df)
    
    print("\n" + "=" * 75)
    print("🎉 SEMUA PROSES INFERENSI & GENERASI SNA SELESAI DENGAN SUKSES!")
    print(f"   Distribusi Sentimen:\n{df['predicted_sentiment'].value_counts().to_string()}")
    print(f"\n   Distribusi 9 Emosi:\n{df['emotion'].value_counts().to_string()}")
    print("=" * 75)

if __name__ == '__main__':
    main()

