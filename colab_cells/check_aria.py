import json
import re

with open('threads_diag.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
count = 0
for d in data:
    if re.search(r'aria-label=[\'"].*?(like|suka|balas|repl|comment|heart|menyukai)[\'"]', d['parent_html'], re.IGNORECASE):
        print(d['text'], "=>", d['parent_html'][:150])
        count += 1
        if count >= 10: break
