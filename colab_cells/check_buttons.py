# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc
import time
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import json

def get_action_bar():
    options = uc.ChromeOptions()
    options.add_argument('--lang=id')
    driver = uc.Chrome(options=options, version_main=153)
    
    url = "https://www.threads.net/@orinnurfayumiii/post/DdJDjZhGeQF"
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(15) # Wait for page load
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # Cari svg yang melambangkan Like (biasanya ada path dengan bentuk tertentu)
    # Atau kita cari div yang role="button" dan isinya ada svg dan teks angka
    buttons = soup.find_all('div', role='button')
    
    results = []
    for btn in buttons:
        text = btn.get_text(strip=True)
        if text.isdigit() or text:
            results.append({
                'text': text,
                'html': str(btn)
            })
            
    with open('threads_buttons.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    print("Selesai")
    driver.quit()

if __name__ == '__main__':
    get_action_bar()
