import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
import json

def diagnose_thread(url):
    options = uc.ChromeOptions()
    options.add_argument('--lang=id')
    driver = uc.Chrome(options=options, version_main=153)
    
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(15) # Wait for load and manual login if needed
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    print("Mencari angka dan svg...")
    # Cari semua elemen yang mengandung text angka
    elements_with_text = soup.find_all(text=True)
    
    results = []
    for text in elements_with_text:
        t = text.strip()
        if t.isdigit() or (t and any(c.isdigit() for c in t)):
            parent = text.parent
            results.append({
                'text': t,
                'tag': parent.name,
                'class': parent.get('class', []),
                'parent_html': str(parent.parent)[:200]
            })
            
    with open('threads_diag.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("Diagnosis selesai. Disimpan di threads_diag.json")
    driver.quit()

if __name__ == '__main__':
    # URL dari salah satu data user
    diagnose_thread("https://www.threads.net/@orinnurfayumiii/post/DdJDjZhGeQF")
