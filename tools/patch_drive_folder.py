import json

nb_path = 'IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb'
with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Update Cell 0 markdown
c0 = ''.join(nb['cells'][0]['source'])
c0 = c0.replace('IndoBERT_SNA', 'IndoBERT_SNA_KEMENPU')
nb['cells'][0]['source'] = [l + '\n' for l in c0.split('\n')]
if nb['cells'][0]['source'][-1] == '\n':
    nb['cells'][0]['source'] = nb['cells'][0]['source'][:-1]

# Update Cell 4
c4 = ''.join(nb['cells'][4]['source'])
old_c4_dir = """DRIVE_DIR = '/content/drive/MyDrive/IndoBERT_SNA'
os.makedirs(DRIVE_DIR, exist_ok=True)"""

new_c4_dir = """# Deteksi otomatis folder IndoBERT_SNA_KEMENPU di Google Drive
possible_dirs = [
    '/content/drive/MyDrive/IndoBERT_SNA_KEMENPU',
    '/content/drive/MyDrive/IndoBERT_SNA'
]
DRIVE_DIR = '/content/drive/MyDrive/IndoBERT_SNA_KEMENPU'
for d in possible_dirs:
    if os.path.exists(d):
        DRIVE_DIR = d
        break

os.makedirs(DRIVE_DIR, exist_ok=True)
print(f"📁 Menggunakan direktori Google Drive: {DRIVE_DIR}")"""

if old_c4_dir in c4:
    c4 = c4.replace(old_c4_dir, new_c4_dir)
    nb['cells'][4]['source'] = [l + '\n' for l in c4.split('\n')]
    if nb['cells'][4]['source'][-1] == '\n':
        nb['cells'][4]['source'] = nb['cells'][4]['source'][:-1]
    print("SUCCESS: Updated Cell 4 DRIVE_DIR")

# Update Cell 18
c18 = ''.join(nb['cells'][18]['source'])
old_c18_dir = """DRIVE_DIR = '/content/drive/MyDrive/IndoBERT_SNA'
TEMP_ZIP = '/content/hasil_training_indobert_sna'"""

new_c18_dir = """# Gunakan DRIVE_DIR yang sudah terdeteksi di Cell 2
if 'DRIVE_DIR' not in globals() or not os.path.exists(DRIVE_DIR):
    DRIVE_DIR = '/content/drive/MyDrive/IndoBERT_SNA_KEMENPU' if os.path.exists('/content/drive/MyDrive/IndoBERT_SNA_KEMENPU') else '/content/drive/MyDrive/IndoBERT_SNA'
TEMP_ZIP = '/content/hasil_training_indobert_sna_kemenpu'"""

if old_c18_dir in c18:
    c18 = c18.replace(old_c18_dir, new_c18_dir)
    c18 = c18.replace('hasil_training_indobert_sna.zip', 'hasil_training_indobert_sna_kemenpu.zip')
    nb['cells'][18]['source'] = [l + '\n' for l in c18.split('\n')]
    if nb['cells'][18]['source'][-1] == '\n':
        nb['cells'][18]['source'] = nb['cells'][18]['source'][:-1]
    print("SUCCESS: Updated Cell 18 DRIVE_DIR and ZIP name")

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("SUCCESS: Notebook updated for IndoBERT_SNA_KEMENPU folder!")

