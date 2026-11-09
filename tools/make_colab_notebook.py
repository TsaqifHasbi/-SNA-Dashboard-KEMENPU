import json
import re
import os

with open('colab_full_pipeline_v2.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'(# =+\s*\n# CELL \d+:.*?\n# =+)'
parts = re.split(pattern, text)

cells = []

# Header markdown cell
intro_text = parts[0].strip().strip('"""').strip()
cells.append({
    'cell_type': 'markdown',
    'metadata': {},
    'source': [line + '\n' for line in intro_text.splitlines()]
})

for i in range(1, len(parts), 2):
    header = parts[i].strip()
    code = parts[i+1].strip()
    
    # Extract cell title
    title = [line for line in header.splitlines() if line.startswith('# CELL')][0].replace('# ', '')
    
    # Create a markdown cell for section header
    cells.append({
        'cell_type': 'markdown',
        'metadata': {},
        'source': [f'## {title}\n']
    })
    
    # Process code
    # Uncomment pip install in Cell 1
    if 'CELL 1' in title:
        code = code.replace('# !pip install', '!pip install')
    
    # Ensure total_memory is used
    code = code.replace('.total_mem /', '.total_memory /')
    
    code_lines = [line + '\n' for line in code.splitlines()]
    if code_lines:
        code_lines[-1] = code_lines[-1].rstrip('\n')
        
    cells.append({
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': code_lines
    })

nb = {
    'cells': cells,
    'metadata': {
        'accelerator': 'GPU',
        'colab': {
            'gpuType': 'T4',
            'provenance': []
        },
        'kernelspec': {
            'display_name': 'Python 3',
            'name': 'python3'
        },
        'language_info': {
            'name': 'python'
        }
    },
    'nbformat': 4,
    'nbformat_minor': 0
}

out_path = 'IndoBERT_SNA_Training_Pipeline.ipynb'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

out_dest = os.path.join('..', 'IndoBERT_SNA_MT_PP', 'IndoBERT_SNA_Training_Pipeline.ipynb')
with open(out_dest, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

code_count = len([c for c in cells if c['cell_type'] == 'code'])
print(f"Generated {out_path} with {len(cells)} total cells ({code_count} code cells).")
print(f"Copied to {out_dest}.")
