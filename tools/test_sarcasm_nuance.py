import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.test_sentiment_page import analyze_text_nlp, detect_topic_from_text
from src.sentiment_corrector import correct_sentiment, align_emotion_valence_9class

test_cases = [
    # 1. Pujian Tulus Standalone
    "WOIII MBG BERGUNA BANGETTT!!!!",
    # 2. Pujian Tulus dengan Konteks Nyata
    "WOIII MBG BERGUNA BANGETTT!!!! adek gua jadi ga kelaparan di sekolah, makasih pak prabowo",
    # 3. Sarkasme: Pujian Diikuti Isu Keracunan
    "WOIII MBG BERGUNA BANGETTT!!!! berguna buat bikin anak orang keracunan massal",
    # 4. Sarkasme: Pujian Diikuti Isu Makanan Basi / Kebohongan
    "WOIII MBG BERGUNA BANGETTT!!!! tapi boong, makanannya basi bray",
    # 5. Sarkasme: Pujian Diikuti Isu Nilep Anggaran
    "WOIII MBG BERGUNA BANGETTT!!!! berguna banget buat nilep anggaran vendor nakal",
    # 6. Pembelaan Kebijakan & Afirmasi Kebaikan
    "bangsat ,udah baik dikasih makan gratis dari mbg"
]

print("=" * 80)
print("PENGUJIAN NUANSA SARKASME VS PUJIAN TULUS (POLICY INTELLIGENCE NLP)")
print("=" * 80)

for text in test_cases:
    res = analyze_text_nlp(text)
    cs, label, score, reason = correct_sentiment(text, res['sentiment'], res['polarity'])
    final_sent = cs if reason else res['sentiment']
    final_pol = score if reason else res['polarity']
    final_emo = align_emotion_valence_9class(text, final_sent, res['primary_emotion'])
    
    print(f"\nKalimat: \"{text}\"")
    print(f"  -> Sentimen Final : {final_sent} (Polaritas: {final_pol:+.2f})")
    print(f"  -> Emosi Final    : {final_emo}")
    print(f"  -> Alasan Aturan  : {reason if reason else 'evaluasi_normal_nlp'}")

print("=" * 80)

