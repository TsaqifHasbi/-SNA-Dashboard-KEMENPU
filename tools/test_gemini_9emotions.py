import os
import json
# pyrefly: ignore [missing-import]
import google.genai as genai

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE'))

prompt = """Kamu ahli analisis sentimen Bahasa Indonesia untuk kebijakan publik (MBG, Koperasi Desa, Sekolah Rakyat).

Labeli setiap teks:
- sentiment: "Positif" / "Netral" / "Negatif"
- emotion (PILIH SALAH SATU DARI 9 KATEGORI):
  * Positif: "Percaya", "Antisipasi", "Joy"
  * Negatif: "Jijik", "Takut", "Sedih", "Marah"
  * Netral: "Surprise", "Informatif"
- confidence: 0.0-1.0
- reason: alasan singkat

Output JSON array saja tanpa markdown:
[{"idx":0,"sentiment":"...","emotion":"...","confidence":0.9,"reason":"..."}]

TEKS:
[0] (twitter/mbg) "Program MBG ini sangat bagus dan kami percaya anak-anak sekolah akan lebih sehat dan bergizi."
[1] (news/mbg) "Ditemukan kasus makanan basi dan berbau busuk berlendir di sekolah X."
[2] (tiktok/mbg) "Pemerintah hari ini mengumumkan alokasi anggaran Rp 71 triliun untuk makan bergizi gratis."
"""

r = client.models.generate_content(
    model='gemini-3.7-flash', contents=prompt,
    config={'temperature': 0.1, 'max_output_tokens': 1024}
)
text = r.text.strip()
if text.startswith('```'):
    text = '\n'.join(text.split('\n')[1:])
    if '```' in text:
        text = text[:text.rfind('```')]
text = text.strip()

print("RAW RESPONSE:")
print(text)

parsed = json.loads(text)
print("\nPARSED:")
for item in parsed:
    print(f"[{item['idx']}] Sentiment: {item['sentiment']}, Emotion: {item['emotion']}, Conf: {item['confidence']}, Reason: {item['reason']}")
