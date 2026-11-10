"""
================================================================================
🚀 MASTER END-TO-END TRAINING & INFERENCE PIPELINE (TERMINAL CLI)
================================================================================
Menjalankan secara terurut langsung dari terminal:
1. Fine-tuning IndoBERT Sentimen (3-Kelas: Positif, Netral, Negatif)
2. Fine-tuning IndoBERT 9-Emosi (Trust, Anticipation, Joy, Disgust, Fear, Sadness, Anger, Surprise, Neutral)
3. Full Corpus Inference (21.047 baris) & Multilayer SNA Graph Generation
================================================================================
"""

import os
import sys
import time
import argparse
import subprocess

# Windows UTF-8 fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_step(step_num, title, cmd):
    print("\n" + "=" * 75)
    print(f"[{step_num}/3] 🚀 {title.upper()}")
    print("=" * 75)
    print(f"Perintah: {cmd}\n")
    t0 = time.time()
    ret = subprocess.run(cmd, shell=True, cwd=BASE_DIR)
    elapsed = time.time() - t0
    if ret.returncode != 0:
        print(f"\n❌ [ERROR] Langkah {step_num} gagal dengan return code {ret.returncode}!")
        sys.exit(ret.returncode)
    print(f"\n✅ [SUKSES] {title} selesai dalam waktu {elapsed:.1f} detik ({elapsed/60:.1f} menit).")

def main():
    parser = argparse.ArgumentParser(description="Master Training & Inference Pipeline KemenPU")
    parser.add_argument('--sentiment-only', action='store_true', help="Hanya jalankan training model sentimen")
    parser.add_argument('--emotion-only', action='store_true', help="Hanya jalankan training model emosi")
    parser.add_argument('--skip-train', action='store_true', help="Lewati training, langsung inferensi & SNA")
    parser.add_argument('--epochs', type=int, default=3, help="Jumlah epoch training (default: 3)")
    parser.add_argument('--batch-size', type=int, default=16, help="Batch size training (default: 16)")
    args = parser.parse_args()

    print("=" * 75)
    print("🚀 PIPELINE TRAINING & INFERENCE INDOBERT KEMENTERIAN PU (TERMINAL)")
    print("=" * 75)

    if not args.skip_train and not args.emotion_only:
        run_step(
            1,
            "Training Model Sentimen IndoBERT V2 (3-Kelas)",
            f"{sys.executable} models/train_indobert.py"
        )

    if not args.skip_train and not args.sentiment_only:
        run_step(
            2,
            "Training Model IndoBERT 9-Emosi Plutchik",
            f"{sys.executable} models/train_indobert_9_emotions.py"
        )

    if not args.sentiment_only and not args.emotion_only:
        run_step(
            3,
            "Inferensi Korpus Lengkap (21.047 Data) & Pembuatan Graf SNA",
            f"{sys.executable} run_local_pipeline.py"
        )

    print("\n" + "=" * 75)
    print("🎉 SELURUH PIPELINE TRAINING & INFERENCE TELAH SELESAI!")
    print("Jalankan dashboard sekarang:")
    print("👉 streamlit run app.py")
    print("=" * 75)

if __name__ == '__main__':
    main()
