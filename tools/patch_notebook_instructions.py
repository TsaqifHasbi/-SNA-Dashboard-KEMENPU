import json

nb_path = 'IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Update Cell 0
cell_0_text = """# PIPELINE LENGKAP: ANOTASI GEMINI + TRAINING INDOBERT + INFERENSI + SNA (KEMEN PU)
============================================================================
ALL-IN-ONE Google Colab Notebook dengan GPU T4
Proyek: Analisis Sentimen & SNA Opini Publik Kementerian PU & Menteri PU (Ir. Dody Hanggodo, M.P.E.)

CARA PAKAI:
  1. Buka Google Drive (akun yang sama dengan Google Colab)
  2. Buat folder baru bernama: IndoBERT_SNA  (di MyDrive / Drive Saya)
  3. Upload file dari folder project lokal (IndoBERT_SNA_MT_KEMENPU/data/):
     - master_scraped_corpus.csv      (Wajib - 15.836 data bersih 7 platform)
     - gold_standard_sample_1000.csv  (Wajib untuk Cell Anotasi Gemini - 1.000 sampel seimbang)
     - train.csv, val.csv, test.csv   (Opsional - dataset latih sentimen)
     - train_emotion_9.csv, val_emotion_9.csv, test_emotion_9.csv (Opsional - dataset latih 9 emosi)
  4. Buka notebook ini di Google Colab:
     - File -> Upload notebook -> pilih file IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb
  5. Pastikan Hardware Acceleration aktif:
     - Klik menu Runtime -> Change runtime type -> Hardware accelerator: GPU (pilih T4 GPU) -> Save
  6. Jalankan Semua Cell:
     - Klik Runtime -> Run All (atau tekan tombol Ctrl + F9)
============================================================================"""

nb['cells'][0]['source'] = [l + '\n' for l in cell_0_text.split('\n')]
if nb['cells'][0]['source'][-1] == '\n':
    nb['cells'][0]['source'] = nb['cells'][0]['source'][:-1]

# Update Cell 6 models fallback
c6_source = ''.join(nb['cells'][6]['source'])
old_c6_models = "for m in ['gemini-3.7-flash', 'gemini-3.8-flash', 'gemini-3.1-flash-lite']:"
new_c6_models = "for m in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-3.7-flash', 'gemini-3.8-flash', 'gemini-3.1-flash-lite']:"
if old_c6_models in c6_source:
    c6_source = c6_source.replace(old_c6_models, new_c6_models)
    nb['cells'][6]['source'] = [l + '\n' for l in c6_source.split('\n')]
    if nb['cells'][6]['source'][-1] == '\n':
        nb['cells'][6]['source'] = nb['cells'][6]['source'][:-1]
    print("SUCCESS: Updated Cell 6 model fallback list!")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("SUCCESS: Updated Cell 0 and Cell 6!")

