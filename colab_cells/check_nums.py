import json

with open('threads_diag.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
for d in data:
    if d['text'].strip() in ['35', '21']:
        print("MATCH:", d['text'])
        print(d['parent_html'])
        print("-" * 50)
