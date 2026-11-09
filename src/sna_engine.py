import os
import re
import networkx as nx
import pandas as pd
# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
from pyvis.network import Network

SENTIMENT_COLORS = {
    'Positif': '#10B981',  # Emerald Green
    'Netral': '#64748B',   # Slate Grey
    'Negatif': '#EF4444',  # Crimson Red
}

EMOTION_COLORS = {
    # Positif (Extended Plutchik)
    'Joy': '#10B981',          # Emerald Green
    'Senang': '#10B981',
    'Percaya': '#06B6D4',      # Cyan / Teal
    'Trust': '#06B6D4',
    'Antisipasi': '#F59E0B',   # Amber
    'Anticipation': '#F59E0B',
    # Negatif
    'Marah': '#EF4444',        # Crimson Red
    'Anger': '#EF4444',
    'Takut': '#8B5CF6',        # Violet / Purple
    'Fear': '#8B5CF6',
    'Jijik': '#84CC16',        # Lime Green / Olive
    'Disgust': '#84CC16',
    'Sedih': '#3B82F6',        # Blue
    'Sadness': '#3B82F6',
    # Netral
    'Surprise': '#A78BFA',     # Lavender
    'Terkejut': '#A78BFA',
    'Informatif': '#64748B',   # Slate Grey
    'Netral': '#64748B',
    'Neutral': '#64748B',
}

def extract_mentions(text):
    if not isinstance(text, str):
        return []
    return re.findall(r'@([A-Za-z0-9_.]+)', text)

def build_sna_network(df, max_nodes=100, topic_filter=None, platform_filter=None, mode='sentiment'):
    """
    Membangun graf SNA interaktif berbobot secara efisien dan ramah memori (zero-copy):
    - mode='sentiment': Node diwarnai berdasarkan sentimen dominan (Positif, Netral, Negatif)
    - mode='emotion': Node diwarnai berdasarkan emosi dominan (Senang, Sedih, Marah, dll.)
    
    Filter:
    - topic_filter: Sekolah_Rakyat, MBG, KDMP, atau Semua
    - platform_filter: Twitter, Facebook, Instagram, YouTube, TikTok, Threads, News, atau Semua
    """
    sub_df = df
    if topic_filter and topic_filter != 'Semua':
        sub_df = sub_df[sub_df['topic'] == topic_filter]

    if platform_filter and platform_filter != 'Semua':
        sub_df = sub_df[sub_df['platform'] == platform_filter]

    G = nx.DiGraph()

    author_sentiments = {}
    author_emotions = {}
    author_platforms = {}
    target_sentiments = {}
    target_emotions = {}

    # Optimasi Memori: Filter HANYA baris yang memiliki karakter mention '@' (instan, 0MB overhead)
    mention_mask = sub_df['cleaned_content'].str.contains('@', regex=False, na=False)
    mention_rows = sub_df[mention_mask]

    for author, content, sent, emo, plat in zip(
        mention_rows['author'],
        mention_rows['cleaned_content'],
        mention_rows.get('sentiment_name', ['Netral'] * len(mention_rows)),
        mention_rows.get('emotion', ['Netral'] * len(mention_rows)),
        mention_rows.get('platform', ['Other'] * len(mention_rows))
    ):
        a_clean = str(author).strip().lower()
        if not a_clean or a_clean in ['nan', 'anonim', 'none', '']:
            continue

        sent_str = str(sent)
        emo_str = str(emo)
        plat_str = str(plat)

        if a_clean not in author_sentiments:
            author_sentiments[a_clean] = {'Positif': 0, 'Netral': 0, 'Negatif': 0}
        author_sentiments[a_clean][sent_str] = author_sentiments[a_clean].get(sent_str, 0) + 1

        if a_clean not in author_emotions:
            author_emotions[a_clean] = {'Senang': 0, 'Sedih': 0, 'Marah': 0, 'Takut': 0, 'Terkejut': 0, 'Jijik': 0, 'Netral': 0}
        author_emotions[a_clean][emo_str] = author_emotions[a_clean].get(emo_str, 0) + 1

        author_platforms[a_clean] = plat_str

        # Ekstraksi mention
        mentions = extract_mentions(content)
        for m in mentions:
            target = m.strip().lower()
            if target and target != a_clean:
                if target not in target_sentiments:
                    target_sentiments[target] = {'Positif': 0, 'Netral': 0, 'Negatif': 0}
                target_sentiments[target][sent_str] = target_sentiments[target].get(sent_str, 0) + 1

                if target not in target_emotions:
                    target_emotions[target] = {}
                target_emotions[target][emo_str] = target_emotions[target].get(emo_str, 0) + 1

                if G.has_edge(a_clean, target):
                    G[a_clean][target]['weight'] += 1
                else:
                    G.add_edge(a_clean, target, weight=1, sentiment=sent_str, emotion=emo_str, platform=plat_str)

    # Fallback jika graph terlalu kecil: ambil top authors tanpa iterrows
    if len(G.nodes()) < 10 and len(sub_df) > 0:
        top_authors_series = sub_df['author'].value_counts().head(max_nodes)
        top_authors = [str(a).strip().lower() for a in top_authors_series.index if str(a).strip().lower() not in ['', 'nan', 'anonim', 'none']]
        
        # Ambil sentimen dominan hanya untuk top authors
        sub_top = sub_df[sub_df['author'].str.lower().isin(top_authors)]
        for a, s, e, p in zip(sub_top['author'], sub_top['sentiment_name'], sub_top['emotion'], sub_top['platform']):
            ac = str(a).strip().lower()
            if ac not in author_sentiments:
                author_sentiments[ac] = {'Positif': 0, 'Netral': 0, 'Negatif': 0}
            author_sentiments[ac][str(s)] = author_sentiments[ac].get(str(s), 0) + 1
            if ac not in author_emotions:
                author_emotions[ac] = {}
            author_emotions[ac][str(e)] = author_emotions[ac].get(str(e), 0) + 1
            author_platforms[ac] = str(p)

        for i in range(len(top_authors) - 1):
            a1 = top_authors[i]
            a2 = top_authors[i+1]
            if a1 != a2:
                G.add_edge(a1, a2, weight=1, sentiment='Netral', emotion='Netral', platform='Lintas')

    # Subgraph first to top nodes before calculating betweenness for sub-second performance
    if len(G.nodes()) > max_nodes:
        top_nodes = sorted(
            G.nodes(),
            key=lambda n: G.in_degree(n) * 2 + G.out_degree(n),
            reverse=True
        )[:max_nodes]
        G = G.subgraph(top_nodes).copy()

    # Calculate betweenness centrality on the top subgraph
    try:
        betweenness = nx.betweenness_centrality(G)
    except Exception:
        betweenness = {n: 0 for n in G.nodes()}

    # Node attributes
    for node in list(G.nodes()):
        # Dominant sentiment (from authored posts, or perceived from incoming mentions)
        s_counts = author_sentiments.get(node)
        if not s_counts or sum(s_counts.values()) == 0:
            s_counts = target_sentiments.get(node, {'Positif': 0, 'Netral': 1, 'Negatif': 0})
        dom_sent = max(s_counts, key=s_counts.get) if s_counts else 'Netral'

        # Dominant emotion (from authored posts, or perceived from incoming mentions)
        e_counts = author_emotions.get(node)
        if not e_counts or sum(e_counts.values()) == 0:
            e_counts = target_emotions.get(node, {'Netral': 1})
        dom_emo = max(e_counts, key=e_counts.get) if e_counts else 'Netral'

        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        bw = round(betweenness.get(node, 0.0), 4)

        if mode == 'emotion':
            color = EMOTION_COLORS.get(dom_emo, '#64748B')
            badge = f"Emosi: <b>{dom_emo}</b>"
        else:
            color = SENTIMENT_COLORS.get(dom_sent, '#64748B')
            badge = f"Sentimen: <b>{dom_sent}</b>"

        size = min(max(12, 12 + in_deg * 2.5), 50)
        clean_node = f"@{str(node).strip().lstrip('@')}"
        tooltip = (
            f"<div style='font-family:Inter,sans-serif; padding:6px;'>"
            f"<b style='color:#38BDF8; font-size:14px;'>{clean_node}</b><br>"
            f"{badge}<br>"
            f"In-Degree (Dirujuk): <b>{in_deg}</b><br>"
            f"Out-Degree (Menyebut): <b>{out_deg}</b><br>"
            f"Betweenness Centrality: <b>{bw}</b><br>"
            f"Platform: {author_platforms.get(node, 'Lintas')}"
            f"</div>"
        )

        G.nodes[node]['sentiment'] = dom_sent
        G.nodes[node]['emotion'] = dom_emo
        G.nodes[node]['color'] = color
        G.nodes[node]['in_degree'] = in_deg
        G.nodes[node]['out_degree'] = out_deg
        G.nodes[node]['betweenness'] = bw
        G.nodes[node]['size'] = size
        G.nodes[node]['title'] = tooltip

    return G

def get_network_metrics(G):
    """Menghitung metrik analitis jaringan untuk pelaporan eksekutif."""
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes == 0:
        return {
            'nodes': 0, 'edges': 0, 'density': 0,
            'avg_degree': 0, 'top_in_degree': [], 'top_betweenness': []
        }

    density = round(nx.density(G), 5)
    degrees = [d for n, d in G.degree()]
    avg_degree = round(np.mean(degrees), 2) if degrees else 0

    top_in = sorted(G.nodes(data=True), key=lambda x: x[1].get('in_degree', 0), reverse=True)[:10]
    top_bw = sorted(G.nodes(data=True), key=lambda x: x[1].get('betweenness', 0), reverse=True)[:10]

    return {
        'nodes': n_nodes,
        'edges': n_edges,
        'density': density,
        'avg_degree': avg_degree,
        'top_in_degree': top_in,
        'top_betweenness': top_bw
    }

def generate_pyvis_html(G, height="620px", mode='sentiment'):
    """
    Menghasilkan kode HTML interaktif physics-network graf Pyvis dengan styling premium.
    """
    net = Network(height=height, width="100%", bgcolor="#0F172A", font_color="#F8FAFC", directed=True)

    for node, data in G.nodes(data=True):
        node_str = str(node).strip().lstrip('@')
        if node_str.startswith('#'):
            clean_node = f"#{node_str.lstrip('#')}"
        else:
            clean_node = f"@{node_str}"
        net.add_node(
            node,
            label=clean_node,
            title=data.get('title', node),
            color=data.get('color', '#64748B'),
            size=data.get('size', 15),
            font={'color': '#F8FAFC', 'size': 11, 'face': 'Inter'},
            borderWidth=2,
            borderWidthSelected=4,
        )

    for u, v, data in G.edges(data=True):
        edge_color = 'rgba(148, 163, 184, 0.25)'
        net.add_edge(u, v, value=data.get('weight', 1), color=edge_color)

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 1.5,
        "shadow": true
      },
      "edges": {
        "color": { "inherit": false },
        "smooth": { "type": "continuous" },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -60,
          "centralGravity": 0.015,
          "springLength": 110,
          "springConstant": 0.06
        },
        "maxVelocity": 40,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 120 }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 150,
        "zoomView": true,
        "navigationButtons": true
      }
    }
    """)

    return net.generate_html()

def export_gephi_gexf(G, filepath):
    """
    Menyimpan graf dalam format standar Gephi (.gexf) dengan sanitasi tipe data ketat
    agar kompatibel dengan NetworkX 3.4+ / Python 3.12-3.14 di lingkungan Cloud.
    """
    try:
        clean_G = nx.DiGraph() if G.is_directed() else nx.Graph()
        
        for n, d in G.nodes(data=True):
            clean_node = str(n).strip()
            clean_G.add_node(
                clean_node,
                label=clean_node,
                sentiment=str(d.get('sentiment') or 'Netral'),
                emotion=str(d.get('emotion') or 'Netral'),
                color=str(d.get('color') or '#64748B'),
                in_degree=int(d.get('in_degree', 0)),
                out_degree=int(d.get('out_degree', 0)),
                betweenness=float(d.get('betweenness', 0.0)),
                size=float(d.get('size', 12.0))
            )

        for u, v, d in G.edges(data=True):
            clean_G.add_edge(
                str(u).strip(),
                str(v).strip(),
                weight=float(d.get('weight', 1.0)),
                sentiment=str(d.get('sentiment') or 'Netral'),
                emotion=str(d.get('emotion') or 'Netral'),
                platform=str(d.get('platform') or 'Semua')
            )

        nx.write_gexf(clean_G, filepath)
        return filepath
    except Exception as e:
        # Fallback jika writer GEXF mengalami kendala serializer
        try:
            min_G = nx.DiGraph() if G.is_directed() else nx.Graph()
            for u, v in G.edges():
                min_G.add_edge(str(u).strip(), str(v).strip())
            nx.write_gexf(min_G, filepath)
            return filepath
        except Exception:
            return None
