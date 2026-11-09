"""
Langkah 2: Anotasi Gold Standard dengan Gemini API (v3 - robust)
Multi-model fallback + robust parsing + checkpoint resume
"""
import os, sys, io, json, time, re
import pandas as pd
# pyrefly: ignore [missing-import]
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_KEY = "YOUR_GEMINI_API_KEY_HERE"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
INPUT_PATH = os.path.join(DATA_DIR, 'gold_standard_sample_1000.csv')
OUTPUT_PATH = os.path.join(DATA_DIR, 'gold_standard_annotated_1000.csv')
CHECKPOINT_PATH = os.path.join(DATA_DIR, 'annotation_checkpoint.json')

BATCH_SIZE = 5
MODELS = ['gemini-3.5-flash', 'gemini-3.7-flash', 'gemini-3.1-flash-lite']

client = genai.Client(api_key=API_KEY)

PROMPT = """Kamu ahli analisis sentimen Bahasa Indonesia untuk kebijakan publik (MBG, Koperasi Desa, Sekolah Rakyat).

Label setiap teks dengan:
- sentiment: "Positif" / "Netral" / "Negatif"
- emotion: "Senang" / "Sedih" / "Marah" / "Takut" / "Terkejut" / "Jijik" / "Netral"
- confidence: 0.0-1.0
- reason: alasan singkat

PENTING: Pahami KONTEKS, bukan kata per kata.
- "Tidak gagal, berhasil" = Positif
- "Keracunan setelah makan MBG" = Negatif
- "Cacing dalam makanan" = Negatif
- "Bagus tapi banyak masalah" = Negatif

Output JSON array saja, tanpa markdown:
[{{"idx":0,"sentiment":"...","emotion":"...","confidence":0.9,"reason":"..."}}]

TEKS:
{texts}"""


def build_prompt(batch_df):
    texts = ""
    for i, (_, row) in enumerate(batch_df.iterrows()):
        t = str(row['cleaned_content'])[:400]
        texts += f'\n[{i}] ({row["platform"]}/{row["topic"]}) "{t}"\n'
    return PROMPT.format(texts=texts)


def parse(text, expected_n):
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:])
        if '```' in text:
            text = text[:text.rfind('```')]
    text = text.strip()

    results = None
    try:
        results = json.loads(text)
    except:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            try:
                results = json.loads(m.group())
            except:
                pass

    if not isinstance(results, list):
        return None

    # Ensure all items are dicts with required keys
    clean = []
    for item in results:
        if isinstance(item, dict) and 'sentiment' in item:
            clean.append(item)
        else:
            clean.append({"idx": len(clean), "sentiment": "Netral", "emotion": "Netral",
                          "confidence": 0.5, "reason": "parsed default"})

    while len(clean) < expected_n:
        clean.append({"idx": len(clean), "sentiment": "Netral", "emotion": "Netral",
                      "confidence": 0.3, "reason": "padding"})
    return clean[:expected_n]


def annotate_batch(batch_df, bn):
    prompt = build_prompt(batch_df)
    n = len(batch_df)

    for model in MODELS:
        for attempt in range(2):
            try:
                r = client.models.generate_content(
                    model=model, contents=prompt,
                    config={'temperature': 0.1, 'max_output_tokens': 2048}
                )
                results = parse(r.text, n)
                if results:
                    return results
            except Exception as e:
                err = str(e)
                if '503' in err or '429' in err:
                    time.sleep(3 * (attempt + 1))
                elif '404' in err:
                    break  # skip to next model
                else:
                    time.sleep(1)

    return [{"idx": i, "sentiment": "Netral", "emotion": "Netral",
             "confidence": 0.0, "reason": "all models failed"} for i in range(n)]


def load_cp():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"done": [], "ann": []}

def save_cp(cp):
    with open(CHECKPOINT_PATH, 'w', encoding='utf-8') as f:
        json.dump(cp, f, ensure_ascii=False)


def main():
    print("=" * 70)
    print("ANOTASI GOLD STANDARD DENGAN GEMINI API (v3)")
    print("=" * 70)

    df = pd.read_csv(INPUT_PATH)
    print(f"Total: {len(df):,} sampel")

    cp = load_cp()
    done = set(cp.get("done", cp.get("completed_batches", [])))
    anns = cp.get("ann", cp.get("annotations", []))
    if done:
        print(f"Resume: {len(done)} batches sudah selesai ({len(anns)} annotations)")

    batches = [df.iloc[i:i+BATCH_SIZE] for i in range(0, len(df), BATCH_SIZE)]
    total = len(batches)
    print(f"Batches: {total} | Models: {MODELS}")
    print()

    t0 = time.time()
    new_done = 0

    for bn, bdf in enumerate(batches):
        if bn in done:
            continue

        results = annotate_batch(bdf, bn + 1)

        for i, (di, row) in enumerate(bdf.iterrows()):
            r = results[i] if i < len(results) else {}
            if not isinstance(r, dict):
                r = {"sentiment": "Netral", "emotion": "Netral", "confidence": 0.0, "reason": "bad type"}

            anns.append({
                "original_index": int(di),
                "platform": row['platform'],
                "topic": row['topic'],
                "cleaned_content": str(row['cleaned_content'])[:500],
                "old_sentiment": str(row.get('sentiment_name', '')),
                "old_emotion": str(row.get('emotion', '')),
                "gemini_sentiment": r.get('sentiment', 'Netral'),
                "gemini_emotion": r.get('emotion', 'Netral'),
                "gemini_confidence": float(r.get('confidence', 0.5)),
                "gemini_reason": str(r.get('reason', '')),
            })

        done.add(bn)
        new_done += 1

        if (bn + 1) % 10 == 0 or (bn + 1) == total:
            cp["done"] = list(done)
            cp["ann"] = anns
            save_cp(cp)

        elapsed = time.time() - t0
        remaining = total - len(done)
        eta = (elapsed / max(new_done, 1)) * remaining
        pct = len(done) / total * 100
        print(f"  Batch {bn+1}/{total} ({pct:.0f}%) | {elapsed:.0f}s | ETA: {eta:.0f}s | done={len(done)}")

        time.sleep(0.2)

    # Save final
    cp["done"] = list(done)
    cp["ann"] = anns
    save_cp(cp)

    result_df = pd.DataFrame(anns)

    vs = {'Positif', 'Netral', 'Negatif'}
    ve = {'Senang', 'Sedih', 'Marah', 'Takut', 'Terkejut', 'Jijik', 'Netral'}
    result_df['gemini_sentiment'] = result_df['gemini_sentiment'].apply(lambda x: x if x in vs else 'Netral')
    result_df['gemini_emotion'] = result_df['gemini_emotion'].apply(lambda x: x if x in ve else 'Netral')

    result_df['sentiment_label'] = result_df['gemini_sentiment'].map({'Negatif': 0, 'Netral': 1, 'Positif': 2})
    result_df['emotion_label'] = result_df['gemini_emotion'].map(
        {'Netral': 0, 'Senang': 1, 'Sedih': 2, 'Marah': 3, 'Takut': 4, 'Terkejut': 5, 'Jijik': 6}
    )

    result_df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

    tt = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"SELESAI! ({tt:.0f}s / {tt/60:.1f} menit)")
    print(f"{'=' * 70}")
    print(f"Total anotasi: {len(result_df):,}")
    print(f"\nSentimen (Gemini):")
    print(result_df['gemini_sentiment'].value_counts().to_string())
    print(f"\nEmosi (Gemini):")
    print(result_df['gemini_emotion'].value_counts().to_string())

    changed = (result_df['old_sentiment'] != result_df['gemini_sentiment']).sum()
    print(f"\nSentimen berubah: {changed}/{len(result_df)} ({changed/len(result_df)*100:.1f}%)")

    print(f"\nCross-tab Old vs Gemini:")
    print(pd.crosstab(result_df['old_sentiment'], result_df['gemini_sentiment']).to_string())

    high = (result_df['gemini_confidence'] >= 0.8).sum()
    print(f"\nHigh confidence (>=0.8): {high}/{len(result_df)} ({high/len(result_df)*100:.1f}%)")
    print(f"\nOutput: {OUTPUT_PATH}")

    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)


if __name__ == '__main__':
    main()
