# ==============================================================================
# Laboratorium Uji Sentimen, Emosi & SNA Interaktif (Deep Learning IndoBERT)
# Format Laporan Harian - Slide Deck
# ==============================================================================

import re
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import networkx as nx

from src.mh_style import (
    render_html,
    render_mh_top_bar,
    render_mh_title,
    render_mh_footer,
    render_kpi_chips,
    render_status_badge
)
from src.sna_engine import SENTIMENT_COLORS, EMOTION_COLORS, generate_pyvis_html
from src.sentiment_corrector import SARCASM_PATTERNS, correct_sentiment, align_emotion_valence_9class
from src.indobert_engine import predict_real_indobert
import streamlit.components.v1 as components_v1

# ------------------------------------------------------------------------------
# Leksikon & Bobot Semantik Bahasa Indonesia untuk Kebijakan Publik
# ------------------------------------------------------------------------------
POSITIVE_TERMS = {
    # Keberhasilan, Mutu, Manfaat & Kegunaan
    'baik': 2.5, 'terbaik': 2.8, 'kebaikan': 2.5, 'membaik': 2.5, 'sebaik': 2.2, 'perbaikan': 2.2,
    'bagus': 2.5, 'hebat': 2.5, 'mantap': 2.5, 'mantul': 2.5, 'keren': 2.2, 'berhasil': 2.5,
    'sukses': 2.5, 'bermanfaat': 2.8, 'manfaat': 2.2, 'kemanfaatan': 2.5, 'membantu': 2.5,
    'berguna': 3.0, 'kegunaan': 2.5, 'berfaedah': 2.8, 'faedah': 2.5, 'efektif': 2.8,
    'penting': 2.5, 'berdampak': 2.5, 'tertolong': 2.8, 'menolong': 2.5, 'bernilai': 2.5, 'istimewa': 2.8,
    'terbantu': 2.2, 'bantu': 2.0, 'bantuan': 2.0, 'apresiasi': 2.5, 'mengapresiasi': 2.5,
    'dukung': 2.2, 'mendukung': 2.5, 'dukungan': 2.2, 'terima kasih': 2.2, 'alhamdulillah': 2.8,
    'alhamdulilah': 2.8, 'bersyukur': 2.5, 'syukur': 2.2, 'berkualitas': 2.5, 'kualitas': 2.0,
    # Kebijaksanaan, Kepemimpinan & Intelektual Positif
    'bijak': 3.0, 'bijaksana': 3.2, 'kebijaksanaan': 3.0, 'arif': 2.8, 'kearifan': 2.8,
    'cerdas': 2.5, 'pintar': 2.5, 'jenius': 2.8, 'logis': 2.5, 'rasional': 2.5, 'visioner': 2.8,
    'salut': 2.5, 'jempol': 2.5, 'patut': 2.2, 'pantas': 2.2,
    # Nutrisi, Higienitas, & Kesehatan
    'sehat': 2.5, 'menyehatkan': 2.8, 'kesehatan': 2.2, 'nutrisi': 2.2, 'bergizi': 2.8,
    'gizi': 2.2, 'enak': 2.2, 'nikmat': 2.5, 'lezat': 2.5, 'kenyang': 2.2, 'higienis': 2.5,
    'bersih': 2.2, 'kebersihan': 2.2, 'segar': 2.2,
    # Afeksi, Kecocokan, & Kebenaran
    'benar': 2.2, 'kebenaran': 2.2, 'tepat': 2.5, 'ketepatan': 2.5, 'cocok': 2.2, 'pas': 2.2, 'sesuai': 2.2,
    'suka': 2.2, 'menyukainya': 2.2, 'cinta': 2.5, 'sayang': 2.2, 'peduli': 2.5, 'kepedulian': 2.5,
    # Karakter, Integritas & Keadilan
    'amanah': 2.8, 'terpercaya': 2.5, 'percaya': 2.2, 'kepercayaan': 2.2, 'transparan': 2.8,
    'transparansi': 2.5, 'terbukti': 2.5, 'adil': 2.5, 'keadilan': 2.5, 'merata': 2.5,
    'pemerataan': 2.5, 'layak': 2.2, 'kelayakan': 2.2, 'beres': 2.0, 'tuntas': 2.2,
    'positif': 2.5, 'puas': 2.5, 'memuaskan': 2.5, 'senang': 2.0, 'bangga': 2.2,
    'gembira': 2.0, 'bahagia': 2.5, 'maju': 2.2, 'kemajuan': 2.5, 'tumbuh': 2.0, 'harapan': 2.0,
    'aman': 2.2, 'keamanan': 2.2, 'nyaman': 2.2, 'kenyamanan': 2.2, 'damai': 2.2, 'tenteram': 2.2,
    'murah': 2.0, 'terjangkau': 2.5, 'gratis': 2.0, 'lengkap': 2.0,
    'terobosan': 2.8, 'efisien': 2.5, 'efisiensi': 2.5, 'solusi': 2.5, 'solutif': 2.8,
    'semangat': 2.0, 'berdaya': 2.2, 'optimal': 2.2, 'top': 2.2, 'jos': 2.2, 'joss': 2.2,
    'berkah': 2.5, 'setuju': 2.0, 'pro': 2.0, 'pro rakyat': 2.8, 'juara': 2.5,
    'cerdas': 2.5, 'mencerdaskan': 2.8, 'mencerdaskan bangsa': 3.2, 'mencerdaskan rakyat': 3.0
}

NEGATIVE_TERMS = {
    # Umpatan & Makian Kasar (High intensity Anger/Negatif)
    'anjing': 3.8, 'anjg': 3.8, 'ajg': 3.8, 'babi': 3.5, 'bangsat': 3.5, 'bajingan': 3.5, 'brengsek': 3.2,
    'kontol': 3.8, 'memek': 3.8, 'pantek': 3.5, 'jancuk': 3.8, 'jancok': 3.8,
    'asu': 3.5, 'kampret': 3.0, 'sialan': 3.0, 'tai': 3.2, 'taik': 3.2, 'taek': 3.2,
    'keparat': 3.2, 'bedebah': 3.2, 'biadab': 3.5, 'laknat': 3.0, 'bangke': 3.0,
    'sompret': 2.8, 'setan': 3.0, 'iblis': 3.0, 'dajjal': 3.2,
    'ngentot': 3.8, 'entot': 3.8, 'peler': 3.8, 'jembut': 3.8, 'ngewe': 3.8, 'lonte': 3.8,
    'perek': 3.5, 'jablay': 3.5, 'pecun': 3.5, 'cuks': 3.5, 'cuk': 3.2, 'cok': 3.2,
    'coeg': 2.8, 'ancuk': 3.5, 'ancok': 3.5, 'su': 3.0, 'bajing': 3.2,
    # Pemaksaan, Sikap Arogan & Kediktatoran
    'maksa': 3.2, 'memaksa': 3.2, 'pemaksaan': 3.5, 'dipaksa': 3.0, 'paksakan': 3.2,
    'memaksakan': 3.2, 'arogan': 3.2, 'angkuh': 3.0, 'diktator': 3.5, 'otoriter': 3.5,
    # Ejekan Intelektual & Mental
    'tolol': 3.2, 'goblok': 3.2, 'goblog': 3.2, 'bego': 3.0, 'bloon': 3.0,
    'dungu': 3.2, 'pekok': 3.0, 'idiot': 3.0, 'bodoh': 2.8, 'pembodohan': 3.2, 'sesat': 2.8,
    # Ejekan Politik, Hinaan Relasi, dan Sindiran Sosial
    'kacung': 2.8, 'jongos': 2.8, 'penjilat': 2.8, 'antek': 2.8, 'boneka': 2.5,
    'buzzer': 2.5, 'cebong': 2.5, 'kadrun': 2.5, 'rezim': 2.2, 'komprador': 2.5,
    'budak': 2.5, 'pengkhianat': 3.2, 'khianat': 3.0, 'munafik': 3.0, 'fasik': 2.8,
    # Kritik Mutu, Keluhan, Kehancuran, & Kerusakan
    'negatif': 2.8, 'buruk': 2.5, 'memburuk': 2.5, 'terburuk': 3.0, 'jelek': 2.5, 'kejelekan': 2.8,
    'jahat': 3.0, 'kejahatan': 3.2, 'kejam': 3.0, 'sadis': 3.2, 'zalim': 3.2, 'gagal': 2.8,
    'kegagalan': 2.8, 'rusak': 2.5, 'merusak': 2.8, 'perusak': 3.0, 'kerusakan': 2.8,
    'hancur': 2.8, 'menghancurkan': 3.0, 'kehancuran': 3.0, 'penghancur': 3.0,
    'kecewa': 2.5, 'kekecewaan': 2.8, 'mengecewakan': 2.8, 'rugi': 2.5, 'merugikan': 2.8,
    'dirugikan': 2.8, 'kerugian': 2.8, 'parah': 2.5, 'memperparah': 2.8, 'krisis': 2.5,
    'marah': 2.5, 'kemarahan': 2.8, 'kesal': 2.5, 'geram': 2.5, 'bobrok': 2.8, 'kebobrokan': 3.0,
    'sengsara': 2.5, 'kesengsaraan': 2.8, 'derita': 2.5, 'menderita': 2.8, 'penderitaan': 2.8,
    'susah': 2.2, 'kesusahan': 2.5, 'sulit': 2.2, 'kesulitan': 2.5, 'payah': 2.5, 'kurang': 2.0,
    'beban': 2.2, 'membebani': 2.5, 'masalah': 2.0, 'bermasalah': 2.5, 'amburadul': 2.8,
    'ancam': 2.5, 'ancaman': 2.5, 'mengancam': 2.8, 'terancam': 2.5, 'bahaya': 2.5,
    'berbahaya': 2.8, 'lambat': 2.0, 'tidak adil': 2.8, 'tidak layak': 2.8, 'tidak bermutu': 2.8,
    'tidak baik': 2.8, 'tak baik': 2.8, 'gak baik': 2.8, 'tidak benar': 2.8, 'tidak becus': 3.0,
    'mahal': 2.0, 'sampah': 2.8, 'ampas': 2.8, 'sia-sia': 2.5, 'sia sia': 2.5,
    'mubazir': 2.8, 'boros': 2.5, 'pemborosan': 2.8, 'roboh': 2.8, 'menolak': 2.5,
    'penolakan': 2.5, 'tolak': 2.5, 'protes': 2.5, 'memprotes': 2.5, 'keluhan': 2.2,
    'ngeluh': 2.2, 'kritik': 1.8, 'mengkritik': 2.0, 'kecam': 2.8, 'mengecam': 2.8,
    'kecaman': 2.8, 'batal': 2.2, 'dibatalkan': 2.5, 'kacau': 2.5, 'kekacauan': 2.8,
    'cacat': 2.5, 'mundur': 2.2, 'kemunduran': 2.5, 'kontra': 2.0, 'anti': 2.0,
    'benci': 2.8, 'kebencian': 3.0, 'muak': 2.8, 'eneg': 2.5, 'jengkel': 2.5,
    # Isu Korupsi, Penyalahgunaan & Penyelewengan
    'korupsi': 3.2, 'korup': 3.2, 'bancakan': 3.0, 'curang': 2.8, 'kecurangan': 3.0,
    'disalahgunakan': 3.5, 'menyalahgunakan': 3.5, 'penyalahgunaan': 3.5, 'salahgunakan': 3.5, 'salahguna': 3.5,
    'diselewengkan': 3.5, 'menyelewengkan': 3.5, 'penyelewengan': 3.5, 'menyeleweng': 3.2,
    'salah sasaran': 3.2, 'tidak tepat sasaran': 3.2, 'kurang tepat sasaran': 3.0, 'salah target': 2.8,
    'kurang tepat': 2.8, 'tidak tepat': 2.8, 'salah alokasi': 2.8, 'penyimpangan': 3.2, 'disimpangkan': 3.2,
    'bohong': 2.8, 'kebohongan': 3.0, 'pembohong': 3.0, 'dibohongi': 3.0, 'palsu': 2.5,
    'maling': 3.2, 'rampok': 3.2, 'nilep': 3.0, 'tilep': 3.0, 'sunat': 2.8,
    'pencitraan': 2.5, 'penipuan': 3.0, 'tipu': 2.8, 'manipulasi': 2.8, 'pungli': 3.0,
    'culas': 2.8, 'licik': 2.8, 'kelicikan': 3.0, 'hoax': 2.8, 'fitnah': 3.0,
    # Isu Pemborosan & Anggaran Sia-Sia
    'buang anggaran': 3.5, 'buang-buang anggaran': 3.5, 'buang uang': 3.2, 'buang duit': 3.2,
    'buang-buang uang': 3.5, 'buang-buang duit': 3.5, 'bakar uang': 3.2, 'bakar duit': 3.2,
    'hambur uang': 3.2, 'hambur duit': 3.2, 'hamburkan uang': 3.5, 'buang': 2.2, 'buang-buang': 2.8,
    'sia-sia': 3.2, 'sia sia': 3.2, 'sia': 2.5,
    # Ketiadaan Manfaat, Kesia-siaan & Kekecewaan Efektivitas
    'gada manfaat': 3.5, 'gada manfaatnya': 3.5, 'gaada manfaat': 3.5, 'gaada manfaatnya': 3.5,
    'ga ada manfaat': 3.5, 'ga ada manfaatnya': 3.5, 'gak ada manfaat': 3.5, 'gak ada manfaatnya': 3.5,
    'tidak ada manfaat': 3.5, 'tidak ada manfaatnya': 3.5, 'tak ada manfaat': 3.5, 'kurang bermanfaat': 3.0,
    'gada guna': 3.5, 'gada gunanya': 3.5, 'gaada guna': 3.5, 'gaada gunanya': 3.5,
    'ga ada guna': 3.5, 'ga ada gunanya': 3.5, 'gak ada guna': 3.5, 'gak ada gunanya': 3.5,
    'tidak ada guna': 3.5, 'tidak ada gunanya': 3.5,
    'gada faedah': 3.5, 'gada faedahnya': 3.5, 'gaada faedah': 3.5, 'gaada faedahnya': 3.5,
    'ga ada faedah': 3.5, 'tidak ada faedah': 3.5,
    'gada efek': 3.2, 'gada efeknya': 3.2, 'gaada efek': 3.2, 'ga ada efek': 3.2, 'tidak ada efek': 3.2,
    'gada hasil': 3.2, 'gada hasilnya': 3.2, 'gaada hasil': 3.2, 'ga ada hasil': 3.2, 'tidak ada hasil': 3.2,
    'gada dampak': 3.2, 'gada dampaknya': 3.2, 'tidak ada dampak': 3.2,
    'gada kejelasan': 3.2, 'gaada kejelasan': 3.2, 'ga jelas': 3.0, 'gak jelas': 3.0, 'tidak jelas': 3.0,
    'mana buktinya': 3.2, 'mana hasilnya': 3.2, 'mana janjinya': 3.2, 'mana kerjanya': 3.2,
    'apasi tujuan': 3.2, 'apa sih tujuan': 3.2, 'apa tujuannya': 3.2, 'buat apa sih': 3.0,
    'kok sampe detik ini': 3.2, 'kok sampe sekarang': 3.2, 'kok sampai sekarang': 3.2,
    # Perbandingan Pejoratif Kolonial & Kemunduran Zaman
    'penjajahan': 3.5, 'penjajah': 3.5, 'kolonial': 3.0, 'kolonialisme': 3.2,
    'masa penjajahan': 3.5, 'zaman penjajahan': 3.5, 'jaman penjajahan': 3.5, 'era penjajahan': 3.5,
    'balik masa penjajahan': 3.8, 'balik ke zaman penjajahan': 3.8, 'zaman belanda': 3.2, 'zaman jepang': 3.2,
    'romusha': 3.5, 'kerja rodi': 3.5, '11 12': 2.8, '11-12': 2.8, 'sebelas dua belas': 2.8,
    'tinggal benerin': 2.5, 'malah bukak': 2.8, 'malah buka': 2.5,
    # Hambatan & Ketimpangan
    'terhambat': 2.2, 'hambat': 2.0, 'penghambat': 2.2,
    # Isu Higienitas & Medis (Disgust/Fear)
    'keracunan': 3.5, 'beracun': 3.5, 'racun': 3.5, 'meracuni': 3.5, 'basi': 3.0,
    'bau': 2.5, 'jorok': 2.8, 'kotor': 2.8, 'kekotoran': 2.8, 'tercemar': 3.0, 'kumuh': 2.5,
    'mual': 2.5, 'muntah': 2.8, 'busuk': 3.0, 'najis': 3.0,
    'menjijikkan': 3.0, 'mati': 3.0, 'kematian': 3.0, 'sakit': 2.2, 'penyakit': 2.5
}

# Prefiks & Sufiks Pembentuk Kata Bahasa Indonesia (Morfologi Derivasi)
ID_PREFIXES = ['diper', 'memper', 'meng', 'meny', 'men', 'mem', 'me', 'peng', 'peny', 'pen', 'pem', 'per', 'pe', 'di', 'ter', 'ber', 'ke', 'se']
ID_SUFFIXES = ['kan', 'an', 'i', 'nya', 'lah', 'kah', 'pun']

def normalize_repeated_chars(word):
    """
    Menghasilkan variasi kata dengan mereduksi karakter berulang (elongated words)
    khas gaya penulisan media sosial, misal: 'asuuuu' -> 'asu', 'anjiiing' -> 'anjing', 'paraaah' -> 'parah'.
    """
    variants = {word}
    r1 = re.sub(r'(.)\1{2,}', r'\1', word)
    r2 = re.sub(r'(.)\1{2,}', r'\1\1', word)
    r3 = re.sub(r'(.)\1+', r'\1', word)
    variants.update([r1, r2, r3])
    return variants

def get_morphology_candidates(word):
    """
    Menghasilkan variasi bentuk kata dasar (stem/root) bahasa Indonesia
    guna mengatasi variasi afiksasi dan pemanjangan huruf (misal: asuuuu -> asu, perusak -> rusak).
    """
    raw_variants = normalize_repeated_chars(word)
    cands = set(raw_variants)
    base_words = list(raw_variants)
    for w in list(base_words):
        for suf in ID_SUFFIXES:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                s_word = w[:-len(suf)]
                cands.add(s_word)
                base_words.append(s_word)
    for bw in base_words:
        for pfx in ID_PREFIXES:
            if bw.startswith(pfx) and len(bw) - len(pfx) >= 3:
                rem = bw[len(pfx):]
                cands.add(rem)
                if pfx == 'meny': cands.add('s' + rem)
                elif pfx == 'men': cands.add('t' + rem)
                elif pfx == 'mem': cands.add('p' + rem)
                elif pfx == 'meng': cands.add('k' + rem)
                elif pfx == 'peny': cands.add('s' + rem)
                elif pfx == 'pen': cands.add('t' + rem)
                elif pfx == 'pem': cands.add('p' + rem)
                elif pfx == 'peng': cands.add('k' + rem)
    return cands

EMOTION_KEYWORDS = {
    'Joy': ['senang', 'gembira', 'bahagia', 'suka', 'mantap', 'mantul', 'keren', 'puas', 'bangga', 'alhamdulillah', 'alhamdulilah', 'enak', 'nikmat', 'lezat', 'top', 'joss', 'jos', 'hebat', 'bagus', 'sehat', 'gizi', 'kenyang', 'baik', 'terbaik', 'kebaikan', 'cinta', 'sayang', 'bijak', 'bijaksana', 'salut', 'jempol', 'berguna', 'bermanfaat', 'berfaedah', 'efektif', 'membantu', 'mencerdaskan', 'mencerdaskan bangsa'],
    'Trust': ['percaya', 'dukung', 'transparan', 'amanah', 'terbukti', 'kualitas', 'terjamin', 'sah', 'adil', 'profesional', 'apresiasi', 'berkualitas', 'sehat', 'higienis', 'solutif', 'solusi', 'baik', 'benar', 'tepat', 'peduli', 'aman', 'tepat sasaran', 'bijak', 'bijaksana', 'kebijaksanaan', 'arif', 'cerdas', 'mencerdaskan', 'mencerdaskan bangsa', 'visioner', 'berguna', 'bermanfaat', 'berfaedah', 'efektif', 'membantu'],
    'Anticipation': [
        'harapan', 'semoga', 'nunggu', 'menunggu', 'rencana', 'target', 'potensi', 'peluang', 'prospek', 'nanti', 'ke depan', 'harap', 'tumbuh',
        'harus dipastikan', 'dipastikan', 'diantisipasi', 'jangan sampai', 'tepat sasaran', 'kawal', 'mengawal', 'pengawasan', 'aspirasi', 'dorong', 'mendorong', 'waspada', 'kehati-hatian', 'antisipasi', 'peringatan', 'mitigasi'
    ],
    'Anger': ['marah', 'geram', 'emosi', 'kesal', 'ngamuk', 'anjing', 'babi', 'bangsat', 'bajingan', 'brengsek', 'kontol', 'pantek', 'jancuk', 'jancok', 'asu', 'tolol', 'goblok', 'goblog', 'bego', 'kampret', 'sialan', 'laknat', 'keparat', 'maling', 'korup', 'korupsi', 'rampok', 'nilep', 'bancakan', 'biadab', 'dungu', 'kacung', 'jongos', 'antek', 'penjilat', 'budak', 'pengkhianat', 'perusak', 'merusak', 'rusak', 'hancur', 'negatif', 'mubazir', 'boros', 'protes', 'kecam', 'ngentot', 'entot', 'cuks', 'cuk', 'cok', 'maksa', 'pemaksaan', 'peler', 'jembut', 'lonte', 'ngewe', 'arogan', 'otoriter', 'disalahgunakan', 'penyalahgunaan', 'menyalahgunakan', 'salahguna', 'diselewengkan', 'penyelewengan', 'salah sasaran', 'tidak tepat sasaran', 'kurang tepat', 'tidak tepat', 'penyimpangan', 'buang anggaran', 'buang uang', 'buang duit', 'sia-sia', 'sia sia', 'penjajahan', 'penjajah', 'masa penjajahan', 'zaman penjajahan', 'balik masa penjajahan', 'romusha', 'kerja rodi', '11 12', 'malah bukak', 'malah buka', 'gada manfaat', 'gada manfaatnya', 'gaada manfaat', 'ga ada manfaat', 'gak ada manfaat', 'tidak ada manfaat', 'gada guna', 'gada gunanya', 'gaada guna', 'tidak ada guna', 'apasi tujuan', 'apa sih tujuan', 'kok sampe detik ini'],
    'Disgust': ['jijik', 'basi', 'bau', 'jorok', 'mual', 'muntah', 'busuk', 'najis', 'pencitraan', 'kemunafikan', 'palsu', 'tai', 'taik', 'taek', 'sampah', 'ampas', 'menjijikkan', 'ilfeel', 'hina', 'kacung', 'jongos', 'boneka', 'buzzer', 'munafik', 'mubazir', 'boros', 'pemborosan', 'ngentot', 'peler', 'jembut', 'lonte'],
    'Fear': ['takut', 'khawatir', 'cemas', 'waswas', 'was-was', 'bahaya', 'ancaman', 'keracunan', 'beracun', 'krisis', 'resiko', 'risiko', 'panik', 'seram', 'mengancam'],
    'Sadness': ['sedih', 'kecewa', 'prihatin', 'sengsara', 'kasihan', 'tangis', 'duka', 'rugi', 'merugikan', 'terpuruk', 'terbengkalai', 'miris', 'pilu', 'perusak', 'rusak', 'kegagalan', 'derita', 'sia-sia', 'sia sia', 'memilih pulang', 'putus sekolah', 'terlantar'],
    'Surprise': ['kaget', 'terkejut', 'heran', 'ternyata', 'waduh', 'astaga', 'syok', 'luar biasa', 'tak disangka', 'wow', 'anjir', 'gila'],
    'Neutral': ['siaran pers', 'pengumuman resmi', 'tata tertib', 'berita acara', 'statistik resmi', 'siaran berita']
}

NEGATIONS = {
    'tidak', 'tak', 'bukan', 'jangan', 'belum', 'gak', 'ga', 'nggak', 'tdk', 'kurang',
    'gada', 'gaada', 'kaga', 'kagak', 'nda', 'ndak', 'ngga', 'gk', 'g', 'tanpa', 'nihil', 'nol'
}
INTENSIFIERS = {
    'sangat': 1.6, 'amat': 1.5, 'banget': 1.6, 'bgt': 1.5, 'sekali': 1.5,
    'luar biasa': 1.8, 'parah': 1.6, 'beneran': 1.4, 'sungguh': 1.5,
    'paling': 1.6, 'terlalu': 1.5, 'bener-bener': 1.5, 'bener': 1.3,
    'pol': 1.6, 'bet': 1.5, 'tenan': 1.5, 'pisan': 1.5, 'abis': 1.5, 'habis': 1.4
}

# Pola Frasa Pencegahan & Antisipasi Tata Kelola Kebijakan Publik
PREVENTATIVE_PATTERNS = [
    r'jangan\s+sampai',
    r'(?:harus|perlu|wajib)\s+dipastikan',
    r'(?:harus|perlu|wajib)\s+diantisipasi',
    r'semoga\s+(?:tidak|tak|gak|nggak)',
    r'(?:cegah|mencegah|hindari|menghindari)\s+potensi',
    r'kawal\s+(?:agar|supaya|pelaksanaan)',
    r'(?:agar|supaya)\s+(?:tidak|tak|gak)\s+terjadi',
    r'jangan\s+biarkan',
    r'titip\s+(?:agar|supaya)',
    r'mohon\s+(?:dipastikan|diawasi|dijaga)',
    r'perlu\s+pengawasan'
]

# Pola Pembelaan Kebijakan & Afirmasi Kebaikan Program (Pro-Policy Defense Patterns)
# Mengantisipasi makian/slang yang sebenarnya ditujukan kepada pihak pengkritik atau sebagai kata seru kekaguman
PRO_POLICY_DEFENSE_PATTERNS = [
    # 1. Afirmasi kebaikan program: "udah baik dikasih makan gratis", "udah dibantu sekolah rakyat", "mending dapat makan gratis"
    r'(?:udah|sudah)\s+(?:baik|bagus|enak|gratis|mending|dibantu|dikasih|diberi)\s+',
    r'(?:mending|untung)\s+(?:ada|dikasih|diberi|dapat)\s+(?:mbg|makan\s+gratis|sekolah\s+rakyat|bantuan)',
    # 2. Kurang bersyukur / masih nyinyir: "udah dikasih makan gratis masih aja nyinyir", "udah gratis masih aja protes"
    r'(?:udah|sudah)\s+(?:gratis|dikasih|dibantu).*?(?:masih\s+(?:aja|saja|lu)?\s*(?:protes|nyinyir|ngeluh|bacot|komplain|banyak\s+omong|kurang))',
    r'(?:ga|gak|tidak)\s+(?:tahu\s+diri|bersyukur|tau\s+diri|terima\s+kasih)',
    # 3. Mengecam penentang program: "yang nolak mbg tolol", "buzzer yang jelekin mbg babi"
    r'(?:yang|yg)\s+(?:nolak|nyinyir|hujat|kritik|nyerang|fitnah|benci|gasuka|gak\s+suka|jelek-jelekin|ngejelekin)\s+(?:mbg|kdmp|program|sekolah\s+rakyat).*?\b(?:tolol|goblok|bego|babi|anjing|dungu|kampret|bangsat|sialan)\b',
    # 4. Melarang menjelekkan program: "jangan fitnah mbg anjing"
    r'(?:jangan|jgn|ngapain)\s+(?:fitnah|nyinyir|hujat|jelekin|ngejelekin)\s+(?:mbg|kdmp|program|sekolah\s+rakyat)',
    # 5. Slang penguat pujian (intensifier): "anjir enak banget", "cok mantap pol", "jancuk bergizi tenan"
    r'\b(?:anjir|njir|cok|cuk|cuks|asu|jancuk|jancok|gila|goblok)\b\s+(?:banget\s+)?(?:enak|keren|mantap|mantul|lezat|nikmat|juara|mewah|lengkap|top|kenyang|bagus|berkah|membantu|bergizi)',
    r'\b(?:enak|keren|mantap|mantul|lezat|nikmat|juara|mewah|lengkap|top|kenyang|bagus|bergizi)\b\s+(?:banget|bgt|bet|pol|tenan)?\s*(?:cok|cuk|cuks|anjir|njir|jancok|jancuk|asu)'
]

DEFENSE_VENT_WORDS = {'bangsat', 'anjing', 'babi', 'tolol', 'goblok', 'bego', 'kampret', 'asu', 'jancuk', 'jancok', 'cok', 'cuk', 'cuks', 'sialan', 'setan', 'iblis'}

# ==============================================================================
# DEFINISI TARGET PROGRAM KEBIJAKAN PEMERINTAH (UNTUK DEKOMPOSISI ASPEK / ABSA)
# ==============================================================================
POLICY_TARGET_DEFINITIONS = {
    'MBG': {
        'title': 'Makan Bergizi Gratis (MBG)',
        'agency': 'Badan Gizi Nasional (BGN)',
        'handle': '@BadanGiziNasional',
        'hashtag': '#MBG',
        'keywords': ['mbg', 'mgb', 'makan bergizi', 'makan gratis', 'makan siang gratis', 'bgn', 'badan gizi', 'ompreng']
    },
    'Sekolah Rakyat': {
        'title': 'Program Sekolah Rakyat',
        'agency': 'Kementerian Sosial / Kemendikbud',
        'handle': '@SekolahRakyat_RI',
        'hashtag': '#SekolahRakyat',
        'keywords': ['sekolah rakyat', 'program sekolah rakyat', 'sekolah gratis berasrama', 'sekolah dhuafa', 'putus sekolah', 'siswa sekolah rakyat']
    },
    'KDMP': {
        'title': 'Koperasi Desa Merah Putih (KDMP)',
        'agency': 'Kementerian Koperasi (Kemenkop)',
        'handle': '@Kemenkop_KDMP',
        'hashtag': '#KDMP',
        'keywords': ['kdmp', 'koperasi desa merah putih', 'koperasi desa', 'koperasi merah putih', 'kopdes', 'sembako desa']
    }
}

def detect_present_policies(text):
    text_l = str(text or '').lower()
    found = []
    for policy, d in POLICY_TARGET_DEFINITIONS.items():
        all_indicators = d['keywords'] + [d['handle'].lower(), d['hashtag'].lower()]
        if any(re.search(rf'\b{re.escape(k)}\b', text_l) or (k.startswith(('@', '#')) and k in text_l) for k in all_indicators):
            found.append(policy)
    return found

def detect_topic_from_text(text, fallback="MBG"):
    """
    Mendeteksi topik kebijakan secara mandiri dari isi teks/opini
    agar visualisasi SNA, entitas, dan klaster opini sinkron dengan konten.
    """
    found = detect_present_policies(text)
    if found:
        return found[0]
    return fallback

def decompose_targeted_policy_sentiment(text):
    """
    Melakukan Targeted Sentiment Decomposition (Aspect-Based Sentiment Analysis)
    untuk menguraikan polaritas dan emosi per target kebijakan ketika warganet
    membandingkan lebih dari satu program dalam satu struktur opini komparatif.
    """
    present_policies = detect_present_policies(text)
    if len(present_policies) <= 1:
        single_topic = present_policies[0] if present_policies else 'MBG'
        return {
            'is_multi_target': False,
            'primary_topic': single_topic,
            'topics': [single_topic],
            'evaluations': {}
        }
    
    # Deteksi apakah opini merupakan komparasi pertentangan (contrastive trade-off)
    # atau evaluasi kolektif setara (coordinated multi-target / satu kesatuan)
    CONTRASTIVE_PATTERNS = [
        r'\b(?:daripada|dari pada|ketimbang|dibanding|dibandingkan)\b',
        r'\b(?:mending|mendingan|better|lebih\s+baik)\b',
        r'\b(?:tapi|tetapi|namun|padahal|sedangkan|sementara|seenggaknya|setidaknya)\b',
    ]
    has_contrast = any(re.search(p, text, flags=re.IGNORECASE) for p in CONTRASTIVE_PATTERNS)
    
    topic_clauses = {p: [] for p in present_policies}
    
    if not has_contrast:
        # EVALUASI KOLEKTIF SETARA (SATU KESATUAN):
        # Jika tidak ada konjungsi pertentangan (misal hanya dijeda koma / dan / sama / serta),
        # seluruh kebijakan dievaluasi dalam satu kesatuan kalimat utuh agar sentimennya sinkron.
        for p in present_policies:
            topic_clauses[p].append(text.strip())
    else:
        # KOMPARASI PERTENTANGAN (ASPECT-BASED DECOMPOSITION):
        # Split secara cerdas pada konjungsi kontras dan terminasi kalimat (JANGAN potong pada koma deret!)
        CONTRAST_RE = r'(?:daripada|dari pada|ketimbang|mendingan|mending|better|lebih\s+baik|tapi|tetapi|padahal|sedangkan|sementara|namun|seenggaknya|setidaknya|dibandingkan|dibanding)'
        COMBINED_SEP = rf'([.?!;\n]+|\b(?:{CONTRAST_RE}(?:\s+{CONTRAST_RE})*)\b)'
        
        parts = re.split(COMBINED_SEP, text, flags=re.IGNORECASE)
        fragments = []
        curr = ""
        for part in parts:
            if not part: continue
            part_stripped = part.strip()
            if re.match(r'^[.?!;\n]+$', part_stripped):
                curr += part
                fragments.append(curr.strip(' ,'))
                curr = ""
            elif re.search(rf'^(?:{CONTRAST_RE}(?:\s+{CONTRAST_RE})*)$', part_stripped, re.IGNORECASE):
                if curr.strip(' ,'):
                    fragments.append(curr.strip(' ,'))
                curr = part_stripped + " "
            else:
                curr += part
        if curr.strip(' ,'):
            fragments.append(curr.strip(' ,'))

        # Penelusuran & Perutean Klausa Terarah:
        for frag in fragments:
            frag_l = frag.lower()
            matched_policies = [
                p for p in present_policies
                if any(re.search(rf'\b{re.escape(k)}\b', frag_l) or (k.startswith(('@', '#')) and k in frag_l)
                       for k in POLICY_TARGET_DEFINITIONS[p]['keywords'] + [POLICY_TARGET_DEFINITIONS[p]['handle'].lower(), POLICY_TARGET_DEFINITIONS[p]['hashtag'].lower()])
            ]
            is_contrast_frag = bool(re.search(rf'^(?:{CONTRAST_RE}(?:\s+{CONTRAST_RE})*)\b', frag.strip(), re.IGNORECASE))

            if is_contrast_frag and matched_policies and len(matched_policies) < len(present_policies):
                # Targeted concession / exception (e.g. "tapi seenggaknya sekolah rakyat bisa..."):
                # Menjadi klausa penentu mandiri untuk kebijakan yang dikhususkan
                for p in matched_policies:
                    topic_clauses[p] = [frag]
            else:
                if matched_policies:
                    for p in matched_policies:
                        topic_clauses[p].append(frag)
                else:
                    for p in present_policies:
                        topic_clauses[p].append(frag)

    evaluations = {}
    for p in present_policies:
        clauses_text = " ".join(topic_clauses[p]).strip()
        if not clauses_text:
            clauses_text = text
            
        ana = predict_real_indobert(clauses_text)
        sent = ana['sentiment']
        pol = ana['polarity']
        emo = ana['primary_emotion']
        probs = dict(ana['emotion_probs'])

        evaluations[p] = {
            'topic': p,
            'title': POLICY_TARGET_DEFINITIONS[p]['title'],
            'agency': POLICY_TARGET_DEFINITIONS[p]['agency'],
            'handle': POLICY_TARGET_DEFINITIONS[p]['handle'],
            'hashtag': POLICY_TARGET_DEFINITIONS[p]['hashtag'],
            'sentiment': sent,
            'polarity': pol,
            'confidence': ana['confidence'],
            'primary_emotion': emo,
            'emotion_probs': probs,
            'reason': ana.get('guardrail_applied'),
            'excerpt': clauses_text
        }

    return {
        'is_multi_target': True,
        'is_contrastive': has_contrast,
        'topics': present_policies,
        'evaluations': evaluations
    }

# ------------------------------------------------------------------------------
# Algoritma Inferensi Kalimat
# ------------------------------------------------------------------------------
def analyze_text_nlp(text):
    """
    Melakukan ekstraksi sentimen, 9 emosi, entitas mention, dan hashtag dari teks
    dengan mesin evaluasi morfologi leksikon kontekstual berbobot, dilengkapi
    pendeteksi klausa preventif/antisipasi kebijakan publik.
    """
    if not text or not str(text).strip():
        text = ""

    raw_text = str(text)
    clean_text = raw_text.lower()
    # Normalisasi reduplikasi Indonesia dengan angka 2 atau superscript ² (e.g. "sia²" -> "sia-sia", "lagi²" -> "lagi-lagi", "anak²" -> "anak-anak")
    clean_text = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', clean_text)
    norm_text = re.sub(r'(.)\1+', r'\1', clean_text)
    words = re.findall(r'\b[a-zA-Z0-9_-]+\b', clean_text)
    raw_words = re.findall(r'\b[a-zA-Z0-9_-]+\b', raw_text)
    
    # 1. Ekstraksi Entitas SNA
    mentions = [m.lstrip('@') for m in re.findall(r'@[A-Za-z0-9_.]+', raw_text)]
    hashtags = [h.lstrip('#') for h in re.findall(r'#[A-Za-z0-9_]+', raw_text)]
    
    # Deteksi klausa antisipasi / pencegahan (Preventative Context)
    has_preventative = any(re.search(p, clean_text) or re.search(p, norm_text) for p in PREVENTATIVE_PATTERNS)
    
    # Deteksi klausa pembelaan program / kecaman terhadap penentang (Pro-Policy Defense)
    has_pro_defense = any(re.search(p, clean_text) or re.search(p, norm_text) for p in PRO_POLICY_DEFENSE_PATTERNS)

    # Deteksi sarkasme kontekstual (pujian semu di awal tapi menyerang tajam di kelanjutan isi)
    has_sarcasm = any(re.search(p, clean_text) or re.search(p, norm_text) for p in SARCASM_PATTERNS)
    
    # Temukan batas awal cakupan klausa pencegahan (misal mulai dari "jangan sampai ...")
    prevent_scope_idx = -1
    js_match = re.search(r'\b(?:jangan\s+sampai|agar\s+tidak|supaya\s+tidak|jangan\s+biarkan)\b', clean_text)
    if js_match:
        match_start_char = js_match.start()
        char_count = 0
        for idx, w in enumerate(words):
            char_count = clean_text.find(w, char_count)
            if char_count >= match_start_char:
                prevent_scope_idx = idx
                break
                
    # 2. Perhitungan Skor Sentimen berbasis Morfologi & Frasa
    pos_score = 0.0
    neg_score = 0.0
    caution_score = 0.0

    # Evaluasi umpatan & makian langsung (High-confidence Negatif)
    from src.sentiment_corrector import PROFANITY
    if any(w in PROFANITY for w in words):
        neg_score += 6.0

    # Evaluasi frasa multi-kata (e.g. "buang anggaran", "salah sasaran", "tidak tepat sasaran", "bakar uang")
    for phrase, score in NEGATIVE_TERMS.items():
        if ' ' in phrase and phrase in clean_text:
            neg_score += score * 1.5
    for phrase, score in POSITIVE_TERMS.items():
        if ' ' in phrase and phrase in clean_text:
            neg_pat_p = rf'\b(?:tidak|tak|bukan|jangan|belum|gak|ga|nggak|tdk|kurang|gada|gaada|kaga|kagak|nda|ndak|tanpa)\s+{re.escape(phrase)}\b'
            if re.search(neg_pat_p, clean_text):
                neg_score += score * 1.2
            else:
                pos_score += score
    
    for i, w in enumerate(words):
        is_in_prevent_scope = (prevent_scope_idx != -1 and i >= prevent_scope_idx)
        
        is_negated = False
        if i > 0 and words[i-1] in NEGATIONS:
            is_negated = True
        elif i > 1 and words[i-2] in NEGATIONS:
            is_negated = True

        intensifier_mult = 1.0
        # Cek kata penguat sebelum kata sifat (misal: "sangat berguna", "amat bagus")
        if i > 0:
            cands_prev1 = get_morphology_candidates(words[i-1])
            m_p1 = [INTENSIFIERS[c] for c in cands_prev1 if c in INTENSIFIERS]
            if m_p1: intensifier_mult = max(intensifier_mult, max(m_p1))
        if i > 1:
            cands_prev2 = get_morphology_candidates(words[i-2])
            m_p2 = [INTENSIFIERS[c] for c in cands_prev2 if c in INTENSIFIERS]
            if m_p2: intensifier_mult = max(intensifier_mult, max(m_p2))

        # Cek kata penguat sesudah kata sifat (misal: "berguna bangettt", "enak pol", "mantap bet")
        if i + 1 < len(words):
            cands_next1 = get_morphology_candidates(words[i+1])
            m_n1 = [INTENSIFIERS[c] for c in cands_next1 if c in INTENSIFIERS]
            if m_n1: intensifier_mult = max(intensifier_mult, max(m_n1))
        if i + 2 < len(words):
            cands_next2 = get_morphology_candidates(words[i+2])
            m_n2 = [INTENSIFIERS[c] for c in cands_next2 if c in INTENSIFIERS]
            if m_n2: intensifier_mult = max(intensifier_mult, max(m_n2))
            
        cands = get_morphology_candidates(w)
        pos_matches = [POSITIVE_TERMS[c] for c in cands if c in POSITIVE_TERMS]
        neg_matches = [NEGATIVE_TERMS[c] for c in cands if c in NEGATIVE_TERMS]
        
        best_pos = max(pos_matches) if pos_matches else 0.0
        best_neg = max(neg_matches) if neg_matches else 0.0
        
        # Cek penekanan emosional huruf kapital (ALL CAPS) & kata penguat (intensifier)
        caps_multiplier = 1.25 if (i < len(raw_words) and raw_words[i].isupper() and len(raw_words[i]) >= 3) else 1.0
        best_pos *= (caps_multiplier * intensifier_mult)
        best_neg *= (caps_multiplier * intensifier_mult)
        
        if best_pos > 0 and best_pos >= best_neg:
            if is_negated:
                if is_in_prevent_scope:
                    # Contoh: "jangan sampai tidak merata" -> double negation di klausa pencegahan bermakna afirmatif (harus merata)
                    pos_score += best_pos * 0.8
                    caution_score += 2.0
                else:
                    neg_score += best_pos * 1.2
            else:
                pos_score += best_pos
        elif best_neg > 0:
            if is_negated:
                pos_score += best_neg * 0.8
            else:
                if has_pro_defense and any(c in DEFENSE_VENT_WORDS for c in cands):
                    # Makian/umpatan ditujukan kepada penentang kebijakan atau penegas kekaguman
                    # Tidak membebani penilaian kebijakan, melainkan menambah intensitas pembelaan
                    pos_score += best_neg * 0.5
                elif is_in_prevent_scope:
                    # Kata risiko dalam klausa pencegahan (misal: "jangan sampai pungli/terhambat")
                    # Diperlakukan sebagai kewaspadaan antisipatif (risk mitigation), bukan tuduhan langsung
                    caution_score += best_neg * 1.5
                    neg_score += best_neg * 0.15 # residu kehati-hatian minor
                else:
                    neg_score += best_neg * 1.3

    # Penguatan nilai konstruktif untuk opini yang memuat rekomendasi pencegahan
    if has_preventative:
        pos_score += 1.5
        
    # Penguatan nilai afirmasi pembelaan program dari kritik/nyinyiran
    if has_pro_defense:
        pos_score += 3.0

    # Pembalikan polaritas jika terdeteksi sarkasme (pujian semu di awal yang menyindir tajam di isi)
    if has_sarcasm:
        pos_score = 0.0
        neg_score = max(neg_score + 3.0, 5.0)
        
    diff = pos_score - neg_score
    total_val = pos_score + neg_score
    
    if total_val == 0:
        p_pos = 0.15
        p_neg = 0.15
        p_neu = 0.70
        pred_sent = "Netral"
        polarity = 0.0
    else:
        # Softmax-style scaling
        exp_pos = np.exp(pos_score * 0.8)
        exp_neg = np.exp(neg_score * 0.8)
        exp_neu = np.exp(0.5)
        sum_exp = exp_pos + exp_neg + exp_neu
        p_pos = exp_pos / sum_exp
        p_neg = exp_neg / sum_exp
        p_neu = exp_neu / sum_exp
        
        if diff >= 1.0:
            pred_sent = "Positif"
            polarity = min(1.0, 0.4 + (diff / (total_val + 2)) * 0.6)
        elif diff <= -1.0:
            pred_sent = "Negatif"
            polarity = max(-1.0, -0.4 + (diff / (total_val + 2)) * 0.6)
        else:
            pred_sent = "Netral"
            polarity = float(diff * 0.15)
            
    # 3. Perhitungan 9 Emosi Publik
    emo_scores = {k: 0.1 for k in EMOTION_KEYWORDS.keys()}
    for emo, kw_list in EMOTION_KEYWORDS.items():
        for kw in kw_list:
            # Jika kata kunci positif dinegasikan (misal: "kurang tepat", "tidak percaya", "gada manfaatnya"), lewati dari Trust/Joy/Anticipation
            if emo in ['Joy', 'Trust', 'Anticipation']:
                neg_pat = rf'\b(?:tidak|tak|bukan|jangan|belum|gak|ga|nggak|tdk|kurang|gada|gaada|kaga|kagak|nda|ndak|ngga|gk|tanpa|nihil)\s+(?:\w+\s+)?{re.escape(kw)}\b'
                if re.search(neg_pat, clean_text):
                    continue
            if re.search(rf'\b{re.escape(kw)}\b', clean_text) or re.search(rf'\b{re.escape(kw)}\b', norm_text):
                emo_scores[emo] += 2.8
                
    # Evaluasi kecocokan morfologi emosi per kata
    for i, w in enumerate(words):
        is_w_neg = False
        if i > 0 and words[i-1] in NEGATIONS:
            is_w_neg = True
        elif i > 1 and words[i-2] in NEGATIONS:
            is_w_neg = True

        cands = get_morphology_candidates(w)
        for emo, kw_list in EMOTION_KEYWORDS.items():
            for kw in kw_list:
                if kw in cands:
                    if is_w_neg and emo in ['Joy', 'Trust', 'Anticipation']:
                        emo_scores['Anger'] += 2.2
                        emo_scores['Sadness'] += 1.5
                    else:
                        emo_scores[emo] += 2.5

    # Boost antisipasi & redam amarah jika terdapat klausa pencegahan/tata kelola
    if has_preventative or caution_score > 0:
        emo_scores['Anticipation'] += 5.5 + caution_score * 0.8
        emo_scores['Trust'] += 2.0
        emo_scores['Anger'] = max(0.1, emo_scores['Anger'] * 0.25)
        emo_scores['Disgust'] = max(0.1, emo_scores['Disgust'] * 0.3)

    # Boost kepercayaan & apresiasi jika terdapat pembelaan kebijakan
    if has_pro_defense:
        emo_scores['Trust'] += 5.0
        emo_scores['Joy'] += 2.5
        emo_scores['Anger'] = max(0.2, emo_scores['Anger'] * 0.25)
        emo_scores['Disgust'] = max(0.2, emo_scores['Disgust'] * 0.2)

    # Reaksi emosi sarkasme: rasa jijik (Disgust) dan amarah (Anger) atas sindiran tajam
    if has_sarcasm:
        emo_scores['Disgust'] += 6.0
        emo_scores['Anger'] += 5.0
        emo_scores['Joy'] = 0.05
        emo_scores['Trust'] = 0.05
                
    # Sinkronisasi emosi dengan polaritas sentimen (Sentiment-Valence Constraint)
    if pred_sent == "Positif":
        emo_scores['Joy'] += pos_score * 1.5
        emo_scores['Trust'] += pos_score * 1.2
        emo_scores['Anticipation'] += pos_score * 0.8
        # Redam emosi bertentangan (negatif)
        emo_scores['Anger'] = 0.05
        emo_scores['Disgust'] = 0.05
        emo_scores['Fear'] = 0.05
        emo_scores['Sadness'] = 0.05
    elif pred_sent == "Negatif":
        emo_scores['Anger'] += neg_score * 1.5
        emo_scores['Disgust'] += neg_score * 1.0
        emo_scores['Fear'] += neg_score * 0.8
        emo_scores['Sadness'] += neg_score * 0.8
        # Redam mutlak emosi bertentangan (positif)
        emo_scores['Joy'] = 0.02
        emo_scores['Trust'] = 0.02
        emo_scores['Anticipation'] = 0.02
    else:
        emo_scores['Neutral'] += 2.5
        emo_scores['Surprise'] += 0.5

    sum_emo = sum(emo_scores.values())
    emo_probs = {k: float(v / sum_emo) for k, v in emo_scores.items()}
    primary_emo = max(emo_probs, key=emo_probs.get)
    
    return {
        'sentiment': pred_sent,
        'polarity': polarity,
        'confidence': max(p_pos, p_neg, p_neu),
        'probs': {'Positif': p_pos, 'Netral': p_neu, 'Negatif': p_neg},
        'primary_emotion': primary_emo,
        'emotion_probs': emo_probs,
        'mentions': mentions,
        'hashtags': hashtags
    }

# ------------------------------------------------------------------------------
# Pembangun Graf Relasi SNA Mikro
# ------------------------------------------------------------------------------
def build_micro_sna_graph(author, analysis, topic="MBG", df_corpus=None, targeted_decomp=None):
    """
    Membangun graf jaringan ego mikro berarah menghubungkan Penulis, Sentimen,
    Emosi, Akun Rujukan (@mentions), Tagar (#hashtags), dan Influencer Korpus.
    Mendukung dekomposisi komparasi multi-kebijakan (Directed Aspect Edges).
    """
    G = nx.DiGraph()
    clean_author = f"@{author.strip().lstrip('@')}" if author else "@warganet_opini"
    sent = analysis['sentiment']
    emo = analysis['primary_emotion']
    
    # 1. Central Author Node
    sent_color = SENTIMENT_COLORS.get(sent, '#64748B')
    G.add_node(clean_author, color=sent_color, size=30, shape="dot", title=f"Aktor Pengunggah Opini ({sent})")

    # 2. Multi-Target Policy Connections (jika terdeteksi komparasi lintas kebijakan)
    if targeted_decomp and targeted_decomp.get('is_multi_target'):
        for p, ev in targeted_decomp['evaluations'].items():
            ev_sent = ev['sentiment']
            edge_col = "#10B981" if ev_sent == "Positif" else ("#EF4444" if ev_sent == "Negatif" else "#64748B")
            
            p_node = ev['handle']
            G.add_node(p_node, color="#2563EB", size=26, shape="dot", title=f"Lembaga Target: {ev['agency']} ({ev['title']})")
            G.add_edge(clean_author, p_node, weight=3, color=edge_col, label=f"{ev_sent} ({ev['polarity']:+.2f})")
            
            h_node = ev['hashtag']
            G.add_node(h_node, color="#F59E0B", size=20, shape="square", title=f"Tagar Gerakan: {h_node}")
            G.add_edge(clean_author, h_node, weight=2, color=edge_col, label=f"mengaitkan {h_node}")
    else:
        # Standard Single Topic Mention & Hashtags
        for m in analysis['mentions']:
            m_node = f"@{m.strip().lstrip('@')}"
            if m_node != clean_author:
                G.add_node(m_node, color="#3B82F6", size=22, shape="dot", title=f"Akun Dirujuk / Target Aspirasi: {m_node}")
                G.add_edge(clean_author, m_node, weight=2, label="mentions / rujukan")

        for h in analysis['hashtags']:
            h_node = f"#{h.strip().lstrip('#')}"
            G.add_node(h_node, color="#F59E0B", size=20, shape="square", title=f"Tagar Gerakan / Isu: {h_node}")
            G.add_edge(clean_author, h_node, weight=1, label="mengusung isu")

    # 3. Connect to Real Corpus Influencers (if df_corpus is available)
    if df_corpus is not None and not df_corpus.empty and 'author' in df_corpus.columns:
        sub = df_corpus
        if 'topic' in sub.columns and topic:
            sub_topic = sub[sub['topic'].astype(str).str.upper() == str(topic).upper()]
            if not sub_topic.empty:
                sub = sub_topic
        if 'sentiment_name' in sub.columns:
            sub_sent = sub[sub['sentiment_name'] == sent]
            if not sub_sent.empty:
                sub = sub_sent
        top_kols = sub['author'].dropna().value_counts().head(3).index.tolist()
        for kol in top_kols:
            kol_clean = f"@{str(kol).strip().lstrip('@')}"
            if kol_clean != clean_author and kol_clean not in G.nodes():
                G.add_node(kol_clean, color="#06B6D4" if sent == "Positif" else "#EF4444", size=24, title=f"Aktor Sentral Korpus {topic} ({sent})")
                G.add_edge(kol_clean, clean_author, weight=1, label="kesamaan narasi")
                
    return G

# ------------------------------------------------------------------------------
# Halaman Utama Slide Test Sentimen
# ------------------------------------------------------------------------------
def render_test_sentiment_page(df=None, selected_topic='Kementerian_PU', topic_label=None, date_str='', **kwargs):
    """
    Renders the Interactive Sentiment, Emotion & SNA Laboratory Page.
    """
    render_mh_top_bar(slide_num="Uji")
    render_mh_title(
        "Laboratorium Inferensi Opini Publik",
        "Uji Sentimen, 9 Dimensi Emosi & Pemetaan SNA Interaktif",
        "Eksplorasi respons model Deep Learning IndoBERT terhadap opini publik warganet dan aduan kebijakan secara interaktif."
    )

    fallback_topic = topic_label or selected_topic or "MBG"

    # Presets Kalimat Uji (Tanpa Emoji, Menggunakan Deskripsi Bersih)
    PRESETS = {
        "MBG Positif (Trust & Joy)": "Program Makan Bergizi Gratis (MBG) sangat membantu anak-anak di sekolah dasar mendapatkan nutrisi sehat dan berkualitas! Pedagang katering lokal juga ikut merasakan berkah dan untung @kemdikbud @bapanas #MBG2026 #GenerasiSehat",
        "Aduan Negatif MBG (Anger & Disgust)": "Kecewa sekali dengan distribusi makanan MBG di sekolah kemarin! Makanan basi, jorok, dan ada anak yang mengeluh mual keracunan! Tolong jangan jadikan anggaran rakyat bancakan korupsi! @bpom_ri @dpr_ri #UsutTuntas",
        "KDMP Antisipasi (Harapan Transparansi)": "Koperasi Desa Merah Putih (KDMP) punya prospek dan peluang besar menyejahterakan warga pelosok jika dikelola secara adil, jujur, dan transparan @kemenkopukm #KDMP2026",
        "Sekolah Rakyat Kritis (Perlindungan Sosial)": "Sekolah Rakyat harus dipastikan tepat sasaran bagi anak putus sekolah dan kaum dhuafa, jangan sampai implementasi di lapangan tidak merata dan terhambat pungli @kemensos #PendidikanAdil",
        "Komparasi Kebijakan (MBG vs SR)": "wah gila BGN kerjanya ga becus sampe saat ini masih banyak banget kasus keracunan dari pada buat MBG, mending uangnya buat Sekolah Rakyat lebih bermanfaat buat mereka yang mau belajar dari pada ngeracunin anak mending mencerdaskan anak"
    }

    # Session State Initialization
    if 'test_input_text' not in st.session_state:
        st.session_state.test_input_text = PRESETS["MBG Positif (Trust & Joy)"]
    if 'test_author_handle' not in st.session_state:
        st.session_state.test_author_handle = "warganet_aktif"

    # Container Card Input
    with st.container(border=True):
        st.markdown("<div style='font-size:12px; font-weight:700; color:#0F2942; margin-bottom:6px;'>PILIH CONTOH CEPAT (PRESET):</div>", unsafe_allow_html=True)
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        with col_p1:
            if st.button("MBG Positif", use_container_width=True, help="Uji opini positif MBG"):
                st.session_state.test_input_text = PRESETS["MBG Positif (Trust & Joy)"]
                st.session_state.test_author_handle = "orangtua_siswa"
                st.rerun()
        with col_p2:
            if st.button("Aduan Negatif", use_container_width=True, help="Uji aduan negatif / keracunan"):
                st.session_state.test_input_text = PRESETS["Aduan Negatif MBG (Anger & Disgust)"]
                st.session_state.test_author_handle = "warga_kritis"
                st.rerun()
        with col_p3:
            if st.button("Antisipasi KDMP", use_container_width=True, help="Uji sentimen harapan KDMP"):
                st.session_state.test_input_text = PRESETS["KDMP Antisipasi (Harapan Transparansi)"]
                st.session_state.test_author_handle = "tokoh_desa"
                st.rerun()
        with col_p4:
            if st.button("Sekolah Rakyat", use_container_width=True, help="Uji evaluasi Sekolah Rakyat"):
                st.session_state.test_input_text = PRESETS["Sekolah Rakyat Kritis (Perlindungan Sosial)"]
                st.session_state.test_author_handle = "relawan_pendidikan"
                st.rerun()
        with col_p5:
            if st.button("Komparasi Isu", use_container_width=True, help="Uji dekomposisi opini multitarget (MBG vs Sekolah Rakyat)"):
                st.session_state.test_input_text = PRESETS["Komparasi Kebijakan (MBG vs SR)"]
                st.session_state.test_author_handle = "analis_kebijakan"
                st.rerun()

        c_author, c_text = st.columns([1.2, 3.8])
        with c_author:
            author_input = st.text_input("Akun Pengunggah / Aktor:", value=st.session_state.test_author_handle, help="Identitas akun untuk analisis simpul jaringan (SNA)")
        with c_text:
            text_input = st.text_area(
                "Kalimat / Opini Publik yang Diuji:",
                value=st.session_state.test_input_text,
                height=100,
                help="Ketik atau tempel opini warganet, aduan, atau cuitan untuk diinferensi model IndoBERT"
            )

    # Menjalankan Analisis Deep Learning IndoBERT Asli (PyTorch CPU) + Guardrail
    analysis = predict_real_indobert(text_input)
    sent = analysis['sentiment']
    pol = analysis['polarity']
    emo = analysis['primary_emotion']

    # Deteksi topik secara mandiri dari teks yang diuji (Dynamic Topic Detection)
    active_topic = detect_topic_from_text(text_input, fallback=fallback_topic)

    # Targeted Sentiment Decomposition (Aspect-Based Sentiment Analysis)
    targeted_decomp = decompose_targeted_policy_sentiment(text_input)

    # Penentuan Warna Badge Sentimen & Emosi
    if sent == "Positif":
        sent_color = "#10B981"
        sent_bg = "#ECFDF5"
        sent_icon = "check_circle"
    elif sent == "Negatif":
        sent_color = "#EF4444"
        sent_bg = "#FEF2F2"
        sent_icon = "error"
    else:
        sent_color = "#64748B"
        sent_bg = "#F8FAFC"
        sent_icon = "help"

    emo_hex = EMOTION_COLORS.get(emo, "#2563EB")

    # Interpretasi Emosi terhadap Kebijakan Publik
    EMOTION_POLICY_DESC = {
        'Trust': 'Mencerminkan kepercayaan, apresiasi, kepatuhan, dan legitimasi positif publik terhadap program.',
        'Joy': 'Mencerminkan rasa senang, kepuasan emosional, dan sambutan hangat warga atas manfaat langsung.',
        'Anticipation': 'Mencerminkan harapan tinggi, ekspektasi, dan perhatian publik atas kelanjutan dan tata kelola program.',
        'Anger': 'Mencerminkan kemarahan, protes keras, kejengkelan atas ketidaksesuaian janji atau dugaan penyimpangan.',
        'Disgust': 'Mencerminkan keengganan, mual, kekecewaan mendalam atas kualitas fisik makanan atau praktik curang.',
        'Fear': 'Mencerminkan kekhawatiran risiko kesehatan, keracunan, beban finansial, atau ketidakpastian nasib program.',
        'Sadness': 'Mencerminkan kesedihan atas ketimpangan, empati terhadap korban, atau rasa kecewa yang mendalam.',
        'Surprise': 'Mencerminkan keterkejutan publik atas lonjakan anggaran, temuan mendadak, atau perubahan kebijakan drastis.',
        'Neutral': 'Mencerminkan penyampaian fakta objektif, pelaporan berita, regulasi birokrasi, atau statistik dingin.'
    }

    # ==========================================================================
    # TAMPILAN KARTU HASIL INFERENSI
    # ==========================================================================
    st.write("")
    if targeted_decomp.get('is_multi_target'):
        if targeted_decomp.get('is_contrastive'):
            b_title = "TARGETED SENTIMENT DECOMPOSITION (ASPECT-BASED CONTRAST)"
            b_desc = "Terdeteksi perbandingan kontras lintas kebijakan publik. Model mengurai polaritas & dimensi emosi secara terpisah per target program."
            b_badge = "MULTI-TARGET CONTRAST"
        else:
            b_title = "TARGETED SENTIMENT EVALUATION (COLLECTIVE MULTI-POLICY OPINION)"
            b_desc = "Terdeteksi evaluasi kebijakan kolektif (subjek majemuk setara). Seluruh program dianalisis dalam satu kesatuan opini publik yang utuh."
            b_badge = "MULTI-POLICY CO-EVALUATION"

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #2563EB 100%); color: #FFFFFF; padding: 14px 20px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: rgba(255, 255, 255, 0.12); width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="18" cy="6" r="3"></circle>
                        <circle cx="6" cy="18" r="3"></circle>
                        <path d="M18 9v2a4 4 0 0 1-4 4H6"></path>
                    </svg>
                </div>
                <div>
                    <div style="font-size: 13px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;">{b_title}</div>
                    <div style="font-size: 12px; color: rgba(255, 255, 255, 0.88); margin-top: 2px;">
                        {b_desc}
                    </div>
                </div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.15); padding: 5px 12px; border-radius: 6px; font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px; white-space: nowrap; border: 1px solid rgba(255, 255, 255, 0.25);">
                {b_badge}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        num_targets = len(targeted_decomp['evaluations'])
        cols_target = st.columns(num_targets)
        for idx, (p_name, ev) in enumerate(targeted_decomp['evaluations'].items()):
            p_sent = ev['sentiment']
            p_pol = ev['polarity']
            p_emo = ev['primary_emotion']
            p_emo_hex = EMOTION_COLORS.get(p_emo, "#2563EB")
            if p_sent == "Positif":
                t_color = "#10B981"
                t_bg = "#ECFDF5"
                badge_icon = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:4px;"><polyline points="20 6 9 17 4 12"></polyline></svg>'
            elif p_sent == "Negatif":
                t_color = "#EF4444"
                t_bg = "#FEF2F2"
                badge_icon = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:4px;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
            else:
                t_color = "#64748B"
                t_bg = "#F8FAFC"
                badge_icon = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:4px;"><line x1="5" y1="12" x2="19" y2="12"></line></svg>'
                
            with cols_target[idx]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="border-top: 3px solid {t_color}; margin: -1rem -1rem 12px -1rem; padding: 0;"></div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; min-height:50px;">
                        <div style="flex:1; padding-right:8px;">
                            <div style="font-size:9.5px; font-weight:800; color:#64748B; letter-spacing:0.5px; text-transform:uppercase;">Target Evaluasi Kebijakan</div>
                            <div style="font-size:15px; font-weight:800; color:#0F2942; line-height:1.25; margin-top:2px;">{ev['title']}</div>
                        </div>
                        <span style="background:{t_bg}; color:{t_color}; font-size:12px; font-weight:800; padding:4px 10px; border-radius:6px; border:1px solid {t_color}40; display:inline-flex; align-items:center; flex-shrink:0;">
                            {badge_icon}{p_sent.upper()}
                        </span>
                    </div>
                    <div style="font-size:11px; color:#2563EB; font-weight:600; min-height:32px; margin-top:4px; line-height:1.3;">
                        {ev['agency']} <span style="color:#64748B; font-weight:500;">({ev['handle']})</span>
                    </div>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:6px; margin:12px 0;">
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:6px 4px; text-align:center;">
                            <div style="font-size:9px; font-weight:700; color:#64748B; text-transform:uppercase;">Polaritas</div>
                            <div style="font-size:13px; font-weight:800; color:{t_color}; margin-top:2px;">{p_pol:+.2f}</div>
                        </div>
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:6px 4px; text-align:center;">
                            <div style="font-size:9px; font-weight:700; color:#64748B; text-transform:uppercase;">Keyakinan</div>
                            <div style="font-size:13px; font-weight:800; color:#1E293B; margin-top:2px;">{ev['confidence']*100:.1f}%</div>
                        </div>
                        <div style="background:{p_emo_hex}15; border:1px solid {p_emo_hex}40; border-radius:6px; padding:6px 4px; text-align:center;">
                            <div style="font-size:9px; font-weight:700; color:{p_emo_hex}; text-transform:uppercase;">Emosi</div>
                            <div style="font-size:13px; font-weight:800; color:{p_emo_hex}; margin-top:2px;">{p_emo}</div>
                        </div>
                    </div>
                    
                    <div style="font-size:9.5px; font-weight:700; color:#64748B; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.5px;">Klausa Terarah Terkait:</div>
                    <div style="background:#F8FAFC; border-left:3px solid {t_color}; padding:8px 10px; border-radius:0 6px 6px 0; font-size:11px; color:#334155; line-height:1.45; font-style:italic; min-height:64px; display:flex; align-items:center;">
                        "{ev['excerpt']}"
                    </div>
                    <div style="font-size:10.5px; color:#64748B; margin-top:8px; display:flex; justify-content:space-between; align-items:center; border-top:1px solid #F1F5F9; padding-top:6px;">
                        <span>Simpul SNA: <b style="color:#0F2942;">{ev['handle']}</b></span>
                        <span style="color:{t_color}; font-weight:700;">{ev['hashtag']}</span>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        c_res1, c_res2, c_res3 = st.columns([1.6, 1.6, 1.8])
        engine_badge = "INDOBERT NEURAL LIVE" if analysis.get('is_deep_learning') else "INDOBERT HYBRID LIVE"

        with c_res1:
            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; font-weight:800; color:#64748B; letter-spacing:0.5px; text-transform:uppercase;">Prediksi Sentimen (IndoBERT)</span>
                    <span style="background:#EEF2FF; color:#4F46E5; font-size:9.5px; font-weight:700; padding:2px 8px; border-radius:4px; border:1px solid #C7D2FE;">{engine_badge}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px; margin:8px 0;">
                    <span style="background:{sent_bg}; color:{sent_color}; font-size:22px; font-weight:800; padding:4px 14px; border-radius:8px; border:1px solid {sent_color}40;">
                        {sent.upper()}
                    </span>
                </div>
                <div style="font-size:12px; color:#475569;">Keyakinan Model: <b>{analysis['confidence']*100:.1f}%</b></div>
                <div style="font-size:11.5px; color:#64748B; margin-top:4px;">Skor Polaritas Kontinu: <b>{pol:+.2f}</b> (Skala -1.0 s/d +1.0)</div>
                """, unsafe_allow_html=True)
                
                # Progress bar probabilitas
                st.progress(float(analysis['probs'].get(sent, 0.5)))

        with c_res2:
            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; font-weight:800; color:#64748B; letter-spacing:0.5px; text-transform:uppercase;">9 Dimensi Emosi (Plutchik)</span>
                    <span style="background:#F0FDF4; color:#16A34A; font-size:9.5px; font-weight:700; padding:2px 8px; border-radius:4px; border:1px solid #BBF7D0;">PLUTCHIK 9-CLASS</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px; margin:8px 0;">
                    <span style="background:{emo_hex}15; color:{emo_hex}; font-size:22px; font-weight:800; padding:4px 14px; border-radius:8px; border:1px solid {emo_hex}40;">
                        {emo}
                    </span>
                </div>
                <div style="font-size:12px; color:#475569;">Intensitas Emosi: <b>{analysis['emotion_probs'][emo]*100:.1f}%</b></div>
                <div style="font-size:11px; color:#64748B; margin-top:4px; line-height:1.4;">
                    {EMOTION_POLICY_DESC.get(emo, '')}
                </div>
                """, unsafe_allow_html=True)

        with c_res3:
            with st.container(border=True):
                mentions_str = ", ".join([f"@{m}" for m in analysis['mentions']]) if analysis['mentions'] else "Tidak ada"
                hashtags_str = ", ".join([f"#{h}" for h in analysis['hashtags']]) if analysis['hashtags'] else "Tidak ada"
                st.markdown(f"""
                <div style="font-size:11px; font-weight:800; color:#64748B; letter-spacing:0.5px;">ENTITAS SNA & RUJUKAN KEBIJAKAN</div>
                <div style="font-size:12px; color:#0F2942; margin-top:8px;">
                    Akun Penulis: <b>@{author_input.lstrip('@')}</b><br>
                    Target Rujukan: <b>{mentions_str}</b><br>
                    Tagar Gerakan: <b>{hashtags_str}</b><br>
                    Fokus Topik: <b>{active_topic}</b>
                </div>
                <div style="font-size:11px; color:#2563EB; font-weight:600; margin-top:6px;">
                    Terdifusi ke klaster opini {sent.lower()}
                </div>
                """, unsafe_allow_html=True)

    # ==========================================================================
    # VISUALISASI DETIL: PROBABILITAS EMOSI & GRAF SNA MIKRO
    # ==========================================================================
    st.write("")
    c_chart, c_sna = st.columns([1.8, 3.2])

    with c_chart:
        with st.container(border=True):
            if targeted_decomp.get('is_multi_target'):
                st.markdown("<div style='font-size:12px; font-weight:700; color:#0F2942; margin-bottom:8px;'>KOMPARASI EMOSI LINTAS KEBIJAKAN</div>", unsafe_allow_html=True)
                fig_emo = go.Figure()
                
                # Distinct Policy Palette: tiap kebijakan memiliki palet warna identitas khusus agar tidak tercampur merah/hijau seragam
                POLICY_CHART_COLORS = {
                    'MBG': '#2563EB',             # Royal Blue
                    'Sekolah Rakyat': '#059669',    # Emerald Green
                    'KDMP': '#D97706'              # Amber Gold
                }
                DEFAULT_PALETTE = ['#2563EB', '#059669', '#D97706', '#7C3AED', '#DB2777', '#0891B2']
                
                # Tentukan kategori emosi terpadu (shared categories) across all policies
                # Ambil 5 emosi dengan nilai puncak tertinggi dari salah satu kebijakan
                peak_scores = {}
                for ev in targeted_decomp['evaluations'].values():
                    for emo_name, prob in ev['emotion_probs'].items():
                        peak_scores[emo_name] = max(peak_scores.get(emo_name, 0.0), prob)
                
                top_shared_emos = [k for k, _ in sorted(peak_scores.items(), key=lambda x: x[1], reverse=True)[:5]]
                y_categories = top_shared_emos[::-1]  # Dibalik agar nilai terbesar tampil paling atas
                
                max_val_found = 0.0
                for idx, (p_name, ev) in enumerate(targeted_decomp['evaluations'].items()):
                    p_col = POLICY_CHART_COLORS.get(p_name, DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)])
                    e_vals = [round(ev['emotion_probs'].get(e_k, 0.0) * 100, 1) for e_k in y_categories]
                    if e_vals:
                        max_val_found = max(max_val_found, max(e_vals))
                    
                    fig_emo.add_trace(go.Bar(
                        name=f"{p_name} ({ev['sentiment']})",
                        y=y_categories,
                        x=e_vals,
                        orientation='h',
                        marker=dict(color=p_col, line=dict(width=0)),
                        text=[f"{v:.1f}%" if v >= 1.0 else "" for v in e_vals],
                        textposition='outside',
                        cliponaxis=False,
                        textfont=dict(color='#334155', size=10, family='Plus Jakarta Sans, sans-serif'),
                        hovertemplate=f"<b>{p_name}</b> ({ev['sentiment']})<br>%{{y}}: <b>%{{x:.1f}}%</b><extra></extra>"
                    ))
                    
                fig_emo.update_layout(
                    barmode='group',
                    bargap=0.22,
                    bargroupgap=0.08,
                    height=350,
                    margin=dict(l=10, r=40, t=32, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.04,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10.5, family='Plus Jakarta Sans, sans-serif'),
                        itemclick=False,
                        itemdoubleclick=False
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='#F1F5F9',
                        zeroline=False,
                        ticksuffix='%',
                        tickfont=dict(size=10, color='#64748B'),
                        range=[0, min(100.0, max(max_val_found * 1.32, 25.0))]
                    ),
                    yaxis=dict(
                        showgrid=False,
                        tickfont=dict(size=11, color='#0F2942', family='Plus Jakarta Sans, sans-serif')
                    )
                )
                st.plotly_chart(fig_emo, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='font-size:12px; font-weight:700; color:#0F2942; margin-bottom:8px;'>SPEKTRUM PROBABILITAS 9 EMOSI</div>", unsafe_allow_html=True)
                sorted_emos = sorted(analysis['emotion_probs'].items(), key=lambda x: x[1], reverse=True)
                e_names = [x[0] for x in sorted_emos]
                e_vals = [round(x[1] * 100, 1) for x in sorted_emos]
                e_colors = [EMOTION_COLORS.get(x, '#64748B') for x in e_names]

                fig_emo = go.Figure(go.Bar(
                    x=e_vals[::-1],
                    y=e_names[::-1],
                    orientation='h',
                    marker=dict(color=e_colors[::-1], line=dict(width=0)),
                    text=[f"{v:.1f}%" for v in e_vals[::-1]],
                    textposition='outside',
                    cliponaxis=False,
                    textfont=dict(color='#334155', size=11, family='Plus Jakarta Sans, sans-serif')
                ))
                fig_emo.update_layout(
                    height=350,
                    margin=dict(l=10, r=40, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=True, gridcolor='#F1F5F9', range=[0, min(100.0, max(e_vals) * 1.28)], zeroline=False, ticksuffix='%'),
                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color='#0F2942', family='Plus Jakarta Sans, sans-serif'))
                )
                st.plotly_chart(fig_emo, use_container_width=True, config={'displayModeBar': False})

    with c_sna:
        with st.container(border=True):
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:12px; font-weight:700; color:#0F2942;">PEMETAAN JEJARING SOSIAL & DIFUSI OPINI (SNA)</span>
                <span style="font-size:10px; font-weight:700; background:#EFF6FF; color:#2563EB; padding:2px 8px; border-radius:4px;">EGO NETWORK INTERAKTIF</span>
            </div>
            """, unsafe_allow_html=True)

            # Bangun Graf SNA Mikro
            G_micro = build_micro_sna_graph(author_input, analysis, topic=active_topic, df_corpus=df, targeted_decomp=targeted_decomp)
            
            # Generate HTML PyVis
            try:
                pyvis_html = generate_pyvis_html(G_micro, height="340px", mode='sentiment')
                components_v1.html(pyvis_html, height=350, scrolling=False)
            except Exception as e:
                # Fallback Plotly Network Diagram jika PyVis terkendala
                pos = nx.spring_layout(G_micro, seed=42)
                edge_x, edge_y = [], []
                for edge in G_micro.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color='#94A3B8'), hoverinfo='none', mode='lines')
                node_x = [pos[node][0] for node in G_micro.nodes()]
                node_y = [pos[node][1] for node in G_micro.nodes()]
                node_colors = [G_micro.nodes[node].get('color', '#64748B') for node in G_micro.nodes()]
                node_texts = list(G_micro.nodes())

                node_trace = go.Scatter(
                    x=node_x, y=node_y, mode='markers+text',
                    text=node_texts, textposition="top center",
                    marker=dict(color=node_colors, size=24, line_width=2, line_color='#FFFFFF'),
                    hoverinfo='text'
                )

                fig_net = go.Figure(data=[edge_trace, node_trace])
                fig_net.update_layout(
                    height=340,
                    margin=dict(l=5, r=5, t=5, b=5),
                    paper_bgcolor='#0F172A',
                    showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                )
                st.plotly_chart(fig_net, use_container_width=True, config={'displayModeBar': False})

            if targeted_decomp.get('is_multi_target'):
                st.markdown("""
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#64748B; margin-top:4px;">
                    <span><b>Relasi Komparasi Terarah:</b> Hijau = Dukungan/Afirmatif | Merah = Kritik/Aduan | Biru = Lembaga Penyelenggara</span>
                    <span>Interaktif: Klik & geser simpul untuk analisis klaster</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#64748B; margin-top:4px;">
                    <span><b>Legenda:</b> Hijau = Opini Positif | Merah = Opini Negatif | Biru = Akun Rujukan (@) | Kuning = Tagar (#)</span>
                    <span>Interaktif: Klik, tahan, atau geser titik untuk eksplorasi relasi</span>
                </div>
                """, unsafe_allow_html=True)

    # Footer Standard
    render_mh_footer(f"Laboratorium Uji Sentimen & Emosi IndoBERT • Korpus Kebijakan Publik {active_topic}")

