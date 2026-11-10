import os, re

files_to_clean = [
    'IndoBERT_SNA_KEMENPU_Training_Pipeline.ipynb',
    'colab_cells/cell_02_config.py',
    'colab_cells/cell_02_config_elektrifikasi.py',
    'colab_cells/tiktok_dump.json',
    'tools/colab_full_pipeline_v2.py',
    'tools/step2_gemini_annotation.py',
    'tools/test_gemini_9emotions.py'
]

pattern = re.compile(r'AQ\.Ab8[A-Za-z0-9_\-]{40,60}')

for fpath in files_to_clean:
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Replace any AQ.Ab8... pattern
    new_content = pattern.sub('YOUR_GEMINI_API_KEY_HERE', content)
    
    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Scrubbed secrets from: {fpath}")
    else:
        print(f"No match in: {fpath}")

print("Secret scrubbing complete!")

