"""
Social Network Analysis (SNA) by Sentiment & Emotion Engine
Tugas Akhir: SNA by Sentiment & 9 Emotions dengan Deep Learning IndoBERT
Referensi: Standar Pemantauan Eksekutif & Dashboard Monitoring Kebijakan Publik
"""

import os
import sys
import re
import json
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import networkx as nx
from collections import defaultdict, Counter

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PARQUET_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.parquet')
CSV_PATH = os.path.join(DATA_DIR, 'enriched_corpus_for_sna.csv')
SNA_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(SNA_OUTPUT_DIR, exist_ok=True)

SENTIMENT_COLORS = {
    'Positif': '#10B981',  # Emerald Green
    'Netral': '#64748B',   # Slate Grey
    'Negatif': '#EF4444',  # Crimson Red
}

EMOTION_COLORS = {
    'Joy': '#10B981', 'Senang': '#10B981',
    'Percaya': '#06B6D4', 'Trust': '#06B6D4',
    'Antisipasi': '#F59E0B', 'Anticipation': '#F59E0B',
    'Marah': '#EF4444', 'Anger': '#EF4444',
    'Takut': '#8B5CF6', 'Fear': '#8B5CF6',
    'Jijik': '#84CC16', 'Disgust': '#84CC16',
    'Sedih': '#3B82F6', 'Sadness': '#3B82F6',
    'Surprise': '#A78BFA', 'Terkejut': '#A78BFA',
    'Informatif': '#64748B', 'Netral': '#64748B'
}

def build_sna_by_sentiment(topic_filter=None, min_interactions=1):
    """
    Membangun Graph SNA Multi-Platform Berdasarkan Sentimen & 9 Emosi IndoBERT:
    - Node: Akun / Tokoh / Media dengan atribut sentimen & emosi
    - Edge: Interaksi (Mentions) dengan atribut sentimen & emosi relasi
    - Sentralitas: In-Degree (KOL), Out-Degree (Buzzer), Betweenness (Broker)
    """
    print("=" * 75)
    print("🌐 MEMBANGUN SOCIAL NETWORK ANALYSIS (SNA) BY SENTIMENT & 9 EMOSI (INDOBERT)")
    print("=" * 75)
    
    if os.path.exists(PARQUET_PATH):
        df = pd.read_parquet(PARQUET_PATH)
    elif os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, low_memory=False)
    else:
        print(f"[!] File dataset {PARQUET_PATH} tidak ditemukan.")
        return None
        
    if topic_filter and topic_filter.lower() != 'all':
        print(f"Filter Topik: {topic_filter}")
        df = df[df['topic'].astype(str).str.lower() == topic_filter.lower()].copy()
        
    print(f"Total baris data yang diproses ke dalam Graf SNA: {len(df):,}")
    
    G = nx.DiGraph()
    author_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    author_emotions = defaultdict(lambda: defaultdict(int))
    author_platforms = {}
    author_engagements = defaultdict(int)
    
    target_sentiments = defaultdict(lambda: {'Positif': 0, 'Netral': 0, 'Negatif': 0})
    target_emotions = defaultdict(lambda: defaultdict(int))
    
    mention_pattern = re.compile(r'@([A-Za-z0-9_\.]+)')
    edges_dict = defaultdict(lambda: {'weight': 0, 'sentiments': [], 'emotions': []})
    
    print("Mengekstraksi simpul (nodes) dan relasi interaksi (edges)...")
    for _, row in df.iterrows():
        source_user = str(row.get('author', row.get('user_id', ''))).strip().lower()
        if not source_user or source_user in ['nan', 'none', 'anonim', '']:
            source_user = f"{row.get('platform', 'Web')}_user"
            
        raw_text = str(row.get('cleaned_content', row.get('raw_content', '')))
        sent = str(row.get('predicted_sentiment', row.get('sentiment_name', 'Netral')))
        emo = str(row.get('emotion_9', row.get('emotion', 'Informatif')))
        eng = int(row.get('total_engagement', 0) if pd.notna(row.get('total_engagement')) else 0)
        platform = str(row.get('platform', 'SocialMedia'))
        
        author_sentiments[source_user][sent] += 1
        author_emotions[source_user][emo] += 1
        author_platforms[source_user] = platform
        author_engagements[source_user] += eng
        
        # Ekstraksi target mention
        mentions = mention_pattern.findall(raw_text)
        for target in mentions:
            target_user = target.strip().lower()
            if target_user and target_user != source_user:
                target_sentiments[target_user][sent] += 1
                target_emotions[target_user][emo] += 1
                edge_key = (source_user, target_user)
                edges_dict[edge_key]['weight'] += 1
                edges_dict[edge_key]['sentiments'].append(sent)
                edges_dict[edge_key]['emotions'].append(emo)
                
    # Tambahkan semua simpul (nodes)
    all_users = set(author_sentiments.keys()).union(set(target_sentiments.keys()))
    print(f"Menambahkan {len(all_users):,} simpul aktor ke graf...")
    
    for user in all_users:
        s_counts = author_sentiments[user] if sum(author_sentiments[user].values()) > 0 else target_sentiments[user]
        dom_sent = max(s_counts, key=s_counts.get) if s_counts else 'Netral'
        
        e_counts = author_emotions[user] if sum(author_emotions[user].values()) > 0 else target_emotions[user]
        dom_emo = max(e_counts, key=e_counts.get) if e_counts else 'Informatif'
        
        pos_cnt = s_counts.get('Positif', 0)
        neg_cnt = s_counts.get('Negatif', 0)
        tot_cnt = sum(s_counts.values())
        actor_nss = round(((pos_cnt - neg_cnt) / tot_cnt * 100), 2) if tot_cnt > 0 else 0.0
        
        G.add_node(
            user,
            platform=author_platforms.get(user, 'Mentioned'),
            sentiment=dom_sent,
            emotion=dom_emo,
            nss=actor_nss,
            total_engagement=author_engagements.get(user, 0),
            color=SENTIMENT_COLORS.get(dom_sent, '#64748B')
        )
        
    # Tambahkan relasi interaksi (edges)
    print(f"Menambahkan {len(edges_dict):,} relasi interaksi...")
    for (src, tgt), data in edges_dict.items():
        if data['weight'] >= min_interactions:
            most_sent = Counter(data['sentiments']).most_common(1)[0][0]
            most_emo = Counter(data['emotions']).most_common(1)[0][0]
            G.add_edge(src, tgt, weight=data['weight'], sentiment=most_sent, emotion=most_emo)
            
    print(f"\n📊 Struktur Graf SNA Berhasil Dibangun:")
    print(f"   • Total Simpul (Nodes) : {G.number_of_nodes():,} entitas")
    print(f"   • Total Sisi (Edges)   : {G.number_of_edges():,} koneksi")
    
    # Hitung Metrik Sentralitas
    print("\nMenghitung metrik sentralitas SNA...")
    in_degrees = dict(G.in_degree(weight='weight'))
    out_degrees = dict(G.out_degree(weight='weight'))
    nx.set_node_attributes(G, in_degrees, 'in_degree')
    nx.set_node_attributes(G, out_degrees, 'out_degree')
    
    top_influencers = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:20]
    print(f"\n🌟 TOP 10 PEMENGARUH UTAMA (TOP INFLUENCERS BY IN-DEGREE):")
    print(f"{'No':<3} {'Username / Akun':<25} {'In-Deg':>8} {'Sentimen':>12} {'Emosi':>12} {'NSS':>8}")
    print("-" * 72)
    top_nodes_data = []
    for i, (u, score) in enumerate(top_influencers, 1):
        nd = G.nodes[u]
        if i <= 10:
            print(f"{i:<3} @{u:<24} {score:>8} {nd['sentiment']:>12} {nd['emotion']:>12} {nd['nss']:>7.1f}%")
        top_nodes_data.append({
            'rank': i, 'user': u, 'in_degree': int(score),
            'out_degree': int(out_degrees.get(u, 0)), 'sentiment': nd['sentiment'],
            'emotion': nd['emotion'], 'nss': nd['nss'],
            'platform': nd['platform'], 'engagement': int(nd['total_engagement'])
        })
        
    # Ekspor Graf Gephi & JSON
    prefix = f"{topic_filter.lower()}_" if topic_filter else "all_topics_"
    gexf_path = os.path.join(SNA_OUTPUT_DIR, f'{prefix}sna_by_sentiment.gexf')
    nx.write_gexf(G, gexf_path)
    print(f"\n💾 File Gephi (.gexf) siap pakai: {gexf_path}")
    
    json_path = os.path.join(SNA_OUTPUT_DIR, f'{prefix}sna_summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(),
            'top_influencers': top_nodes_data
        }, f, indent=4)
    print(f"💾 File Ringkasan JSON tersimpan: {json_path}")
    print("=" * 75)
    return G

if __name__ == '__main__':
    build_sna_by_sentiment()
