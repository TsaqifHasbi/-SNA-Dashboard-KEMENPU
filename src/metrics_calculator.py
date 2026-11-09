# pyrefly: ignore[missing-import]
import numpy as np
import pandas as pd
# pyrefly: ignore[missing-import]
from scipy import stats

def calculate_nss(pos_count, neg_count, total_count):
    """
    Net Sentiment Score (NSS) formula standar pemantauan eksekutif:
    NSS = ((Positif - Negatif) / Total) * 100
    Rentang: -100 s/d +100
    """
    if total_count == 0:
        return 0.0
    return round(((pos_count - neg_count) / total_count) * 100, 2)

def calculate_kpis(df):
    """
    Menghitung 4 Pilar Metrik Inti:
    1. Volume (Total Mentions/Posts)
    2. User (Jumlah Penulis Unik)
    3. Engagement (Likes + Comments + Shares + Reposts)
    4. Reach (Total Estimasi Jangkauan Pemirsa)
    """
    total_volume = len(df)
    unique_users = df['author'].nunique() if total_volume > 0 else 0
    total_engagement = int(df['total_engagement'].sum()) if total_volume > 0 else 0
    total_reach = int(df['reach'].sum()) if 'reach' in df.columns and total_volume > 0 else 0

    counts = df['sentiment_name'].value_counts() if total_volume > 0 else {}
    pos = int(counts.get('Positif', 0))
    net = int(counts.get('Netral', 0))
    neg = int(counts.get('Negatif', 0))

    nss = calculate_nss(pos, neg, total_volume)

    return {
        'volume': total_volume,
        'users': unique_users,
        'engagement': total_engagement,
        'reach': total_reach,
        'positive': pos,
        'neutral': net,
        'negative': neg,
        'nss': nss,
        'pos_pct': round((pos / total_volume) * 100, 1) if total_volume > 0 else 0,
        'net_pct': round((net / total_volume) * 100, 1) if total_volume > 0 else 0,
        'neg_pct': round((neg / total_volume) * 100, 1) if total_volume > 0 else 0,
    }

def calculate_z_test(p1_pos, n1_total, p2_pos, n2_total):
    """
    Uji Beda Proporsi Dua Sampel (Z-Test) ala Laporan Kementerian PU:
    Z = (p1 - p2) / sqrt(p*(1-p)*(1/n1 + 1/n2))
    p = (x1 + x2) / (n1 + n2)
    Taraf Signifikansi 95% (|Z| >= 1.96 -> Nyata, else Derau)
    """
    if n1_total <= 0 or n2_total <= 0:
        return 0.0, 1.0, "DERAU"

    p1 = p1_pos / n1_total
    p2 = p2_pos / n2_total

    p_pool = (p1_pos + p2_pos) / (n1_total + n2_total)
    if p_pool <= 0 or p_pool >= 1:
        return 0.0, 1.0, "DERAU"

    se = np.sqrt(p_pool * (1 - p_pool) * ((1 / n1_total) + (1 / n2_total)))
    if se == 0:
        return 0.0, 1.0, "DERAU"

    z_score = (p1 - p2) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

    status = "NYATA" if abs(z_score) >= 1.96 else "DERAU"
    return round(z_score, 2), round(p_value, 4), status

def calculate_framing_entman(df):
    """
    Analisis 4 Fungsi Framing Entman & Edelman:
    1. Problem Definition
    2. Causal Interpretation
    3. Moral Evaluation
    4. Treatment Recommendation
    """
    total = len(df)
    if total == 0:
        return {}

    text_lower = df['cleaned_content'].str.lower()

    infra_kw = ['bangun', 'gedung', 'konstruksi', 'sekolah', 'ruang', 'fasilitas', 'bantuan', 'proyek', 'sarana']
    tata_kelola_kw = ['anggaran', 'biaya', 'korupsi', 'dprd', 'pejabat', 'menteri', 'dana', 'mutu', 'kualitas', 'tender']
    masalah_kw = ['ambrol', 'rusak', 'bocor', 'lambat', 'gagal', 'keluhan', 'roboh', 'basi', 'keracunan', 'terlantar']
    solusi_kw = ['perbaiki', 'tindak', 'evaluasi', 'inspeksi', 'satgas', 'tuntaskan', 'sanksi', 'prioritas', 'pengawasan']

    c_infra = text_lower.apply(lambda x: any(k in x for k in infra_kw)).sum()
    c_kelola = text_lower.apply(lambda x: any(k in x for k in tata_kelola_kw)).sum()
    c_masalah = text_lower.apply(lambda x: any(k in x for k in masalah_kw)).sum()
    c_solusi = text_lower.apply(lambda x: any(k in x for k in solusi_kw)).sum()

    return {
        'problem_definition': {
            'label': 'Definisi Masalah (Kerusakan Fisik & Fasilitas)',
            'percent': round((c_masalah / total) * 100, 1),
            'count': int(c_masalah)
        },
        'causal_interpretation': {
            'label': 'Penyebab Masalah (Tata Kelola & Mutu Pelaksana)',
            'percent': round((c_kelola / total) * 100, 1),
            'count': int(c_kelola)
        },
        'moral_evaluation': {
            'label': 'Evaluasi Moral (Tuntutan Hak Siswa/Rakyat)',
            'percent': round((c_infra / total) * 100, 1),
            'count': int(c_infra)
        },
        'treatment_recommendation': {
            'label': 'Rekomendasi Solusi (Inspeksi & Sanksi Tegas)',
            'percent': round((c_solusi / total) * 100, 1),
            'count': int(c_solusi)
        }
    }
