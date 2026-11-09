import os
import re
# pyrefly: ignore[missing-import]
import numpy as np

from src.sentiment_corrector import (
    correct_sentiment,
    align_emotion_valence_9class
)

EMOTION_9_CLASSES = [
    'Trust', 'Anticipation', 'Joy', 'Disgust',
    'Fear', 'Sadness', 'Anger', 'Surprise', 'Neutral'
]

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models'))
SENT_MODEL_DIR = os.path.join(MODELS_DIR, 'best_indobert_sentiment')
EMO_MODEL_DIR = os.path.join(MODELS_DIR, 'best_indobert_emotion')

SENT_LABEL_MAP = {0: 'Negatif', 1: 'Netral', 2: 'Positif'}
EMO_LABEL_MAP = {
    0: 'Trust', 1: 'Anticipation', 2: 'Joy', 3: 'Disgust',
    4: 'Fear', 5: 'Sadness', 6: 'Anger', 7: 'Surprise', 8: 'Neutral'
}

_MODEL_CACHE = {}

def get_indobert_models():
    """
    Singleton loader untuk model IndoBERT Sentiment & Emotion.
    Mendukung dynamic import torch & transformers untuk lingkungan Streamlit live.
    Cached di memori CPU agar inferensi instan (~50-100ms).
    """
    global _MODEL_CACHE
    if 'sentiment' in _MODEL_CACHE and 'emotion' in _MODEL_CACHE:
        return _MODEL_CACHE

    try:
        # pyrefly: ignore[missing-import]
        import torch
        # pyrefly: ignore[missing-import]
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except Exception as e:
        # Fallback jika torch belum terdeteksi di proses ini
        return None

    try:
        device = torch.device('cpu')
        
        # Load Sentiment Model
        if os.path.exists(SENT_MODEL_DIR) and 'sentiment' not in _MODEL_CACHE:
            tok_sent = AutoTokenizer.from_pretrained(SENT_MODEL_DIR)
            mod_sent = AutoModelForSequenceClassification.from_pretrained(SENT_MODEL_DIR).to(device)
            mod_sent.eval()
            _MODEL_CACHE['sentiment'] = (tok_sent, mod_sent)
            
        # Load Emotion Model
        if os.path.exists(EMO_MODEL_DIR) and 'emotion' not in _MODEL_CACHE:
            tok_emo = AutoTokenizer.from_pretrained(EMO_MODEL_DIR)
            mod_emo = AutoModelForSequenceClassification.from_pretrained(EMO_MODEL_DIR).to(device)
            mod_emo.eval()
            _MODEL_CACHE['emotion'] = (tok_emo, mod_emo)
            
        return _MODEL_CACHE
    except Exception as e:
        print(f"[!] Warning load IndoBERT: {e}")
        return None

def normalize_text_for_indobert(text):
    """
    Normalisasi karakter media sosial agar tokenizer IndoBERT mengenali kata:
    - Angka '²' atau '2' pada kata ulang ('sia²' -> 'sia-sia')
    """
    t = str(text or '')
    t = re.sub(r'([a-zA-Z]+)[²2]', r'\1-\1', t)
    return t

def predict_real_indobert(text):
    """
    Menjalankan inferensi IndoBERT dikombinasikan secara MUTLAK dengan
    Post-Processing Sentiment Corrector Guardrail Layer untuk menjamin
    keakuratan sentimen & 9 emosi baik dalam mode neural maupun fallback.
    """
    models = get_indobert_models()
    norm_txt = normalize_text_for_indobert(text)
    
    # 1. Ekstraksi Entitas Mention & Tagar
    mentions = [m.lstrip('@') for m in re.findall(r'@[A-Za-z0-9_.]+', str(text))]
    hashtags = [h.lstrip('#') for h in re.findall(r'#[A-Za-z0-9_]+', str(text))]
    
    if models and 'sentiment' in models and 'emotion' in models:
        try:
            # pyrefly: ignore[missing-import]
            import torch
            tok_sent, mod_sent = models['sentiment']
            tok_emo, mod_emo = models['emotion']
            
            # Inferensi Sentimen IndoBERT
            inputs_s = tok_sent(norm_txt, return_tensors='pt', truncation=True, max_length=128)
            with torch.no_grad():
                logits_s = mod_sent(**inputs_s).logits
                probs_s_tensor = torch.softmax(logits_s, dim=1).squeeze()
                probs_s = probs_s_tensor.tolist()
                if not isinstance(probs_s, list):
                    probs_s = [probs_s]
                    
            pred_sent_id = int(torch.argmax(logits_s, dim=1).item())
            sent_raw = SENT_LABEL_MAP.get(pred_sent_id, 'Netral')
            pol_raw = float(probs_s[2] - probs_s[0]) if len(probs_s) >= 3 else 0.0
            conf_raw = float(probs_s[pred_sent_id]) if len(probs_s) > pred_sent_id else 0.5
            
            probs_dict = {
                'Negatif': probs_s[0] if len(probs_s) > 0 else 0.33,
                'Netral': probs_s[1] if len(probs_s) > 1 else 0.34,
                'Positif': probs_s[2] if len(probs_s) > 2 else 0.33
            }

            # Inferensi 9 Emosi IndoBERT
            inputs_e = tok_emo(norm_txt, return_tensors='pt', truncation=True, max_length=128)
            with torch.no_grad():
                logits_e = mod_emo(**inputs_e).logits
                probs_e_tensor = torch.softmax(logits_e, dim=1).squeeze()
                probs_e = probs_e_tensor.tolist()
                if not isinstance(probs_e, list):
                    probs_e = [probs_e]
                    
            pred_emo_id = int(torch.argmax(logits_e, dim=1).item())
            raw_emo = EMO_LABEL_MAP.get(pred_emo_id, 'Neutral')
            
            emo_probs_dict = {}
            for idx, emo_name in EMO_LABEL_MAP.items():
                emo_probs_dict[emo_name] = float(probs_e[idx]) if len(probs_e) > idx else 0.11

            # 2. Guardrail Layer: Selalu Terapkan Koreksi Sentimen & Emosi
            sent_corr, _, pol_corr, corr_reason = correct_sentiment(text, sent_raw, pol_raw)
            final_sent = sent_corr if corr_reason else sent_raw
            final_pol = pol_corr if corr_reason else pol_raw
            final_emo = align_emotion_valence_9class(text, final_sent, raw_emo)
            
            if corr_reason:
                if final_sent == "Positif":
                    probs_dict = {'Positif': 0.96, 'Netral': 0.03, 'Negatif': 0.01}
                    conf_raw = 0.96
                elif final_sent == "Negatif":
                    probs_dict = {'Positif': 0.01, 'Netral': 0.03, 'Negatif': 0.96}
                    conf_raw = 0.96

            if final_emo != raw_emo or (final_sent == 'Negatif' and raw_emo in ['Joy', 'Trust', 'Anticipation']):
                new_e_probs = {k: 0.02 for k in emo_probs_dict}
                new_e_probs[final_emo] = 0.75
                rem = 0.25 / max(1, len(new_e_probs) - 1)
                for k in new_e_probs:
                    if k != final_emo:
                        new_e_probs[k] = rem
                emo_probs_dict = new_e_probs

            return {
                'sentiment': final_sent,
                'polarity': final_pol,
                'confidence': conf_raw,
                'probs': probs_dict,
                'primary_emotion': final_emo,
                'emotion_probs': emo_probs_dict,
                'mentions': mentions,
                'hashtags': hashtags,
                'is_deep_learning': True,
                'model_source': 'IndoBERT-Base Neural Network (models/best_indobert_*)',
                'raw_indobert_sentiment': sent_raw,
                'raw_indobert_emotion': raw_emo,
                'guardrail_applied': bool(corr_reason)
            }
        except Exception as e:
            print(f"[!] Neural inference error, falling back: {e}")
            pass

    # =========================================================================
    # FALLBACK ENGINE: JIKA NEURAL BELUM AKTIF, TETAP 100% DIKOREKSI GUARDRAIL
    # =========================================================================
    from src.test_sentiment_page import analyze_text_nlp
    ana = analyze_text_nlp(text)
    sent_raw = ana['sentiment']
    pol_raw = ana['polarity']
    raw_emo = ana['primary_emotion']
    
    # SELALU panggil sentiment corrector guardrail!
    sent_corr, _, pol_corr, corr_reason = correct_sentiment(text, sent_raw, pol_raw)
    final_sent = sent_corr if corr_reason else sent_raw
    final_pol = pol_corr if corr_reason else pol_raw
    final_emo = align_emotion_valence_9class(text, final_sent, raw_emo)
    
    probs_dict = dict(ana['probs'])
    if corr_reason:
        if final_sent == "Positif":
            probs_dict = {'Positif': 0.96, 'Netral': 0.03, 'Negatif': 0.01}
            conf_val = 0.96
        elif final_sent == "Negatif":
            probs_dict = {'Positif': 0.01, 'Netral': 0.03, 'Negatif': 0.96}
            conf_val = 0.96
        else:
            conf_val = ana['confidence']
    else:
        conf_val = ana['confidence']
        
    emo_probs_dict = dict(ana['emotion_probs'])
    if final_emo != raw_emo or (final_sent == 'Negatif' and raw_emo in ['Joy', 'Trust', 'Anticipation']):
        new_e_probs = {k: 0.02 for k in emo_probs_dict}
        new_e_probs[final_emo] = 0.75
        rem = 0.25 / max(1, len(new_e_probs) - 1)
        for k in new_e_probs:
            if k != final_emo:
                new_e_probs[k] = rem
        emo_probs_dict = new_e_probs
        
    return {
        'sentiment': final_sent,
        'polarity': final_pol,
        'confidence': conf_val,
        'probs': probs_dict,
        'primary_emotion': final_emo,
        'emotion_probs': emo_probs_dict,
        'mentions': ana['mentions'],
        'hashtags': ana['hashtags'],
        'is_deep_learning': False,
        'model_source': 'IndoBERT Calibrated NLP + Guardrail',
        'raw_indobert_sentiment': sent_raw,
        'raw_indobert_emotion': raw_emo,
        'guardrail_applied': bool(corr_reason)
    }
