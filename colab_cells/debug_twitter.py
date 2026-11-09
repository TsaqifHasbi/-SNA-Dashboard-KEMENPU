"""
Debug Twitter: Tes 1 keyword saja dengan logging detail
"""
import time
import urllib.parse
from datetime import datetime, timedelta

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("ERROR: undetected_chromedriver belum terinstall!")
    exit()

# Buka Chrome
print("[1] Membuka Chrome...")
options = uc.ChromeOptions()
options.add_argument('--disable-popup-blocking')
options.add_argument('--lang=id')
driver = uc.Chrome(options=options, version_main=153)

driver.get("https://x.com/login")
print("\n" + "="*60)
print("LOGIN KE TWITTER LALU TEKAN ENTER")
print("="*60)
input(">>> ")

# Cari tweet
keyword = "Makan Bergizi Gratis"
six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
search_q = f"{keyword} lang:id since:{six_months_ago}"
query = urllib.parse.quote(search_q)
url = f"https://x.com/search?q={query}&src=typed_query&f=live"

print(f"\n[2] Membuka URL: {url}")
driver.get(url)

# Tunggu
try:
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
    )
    print("[3] Tweet ditemukan di halaman!")
except:
    print("[3] GAGAL menemukan tweet dalam 15 detik!")

time.sleep(3)

# Cek berapa article yang ada
count_js = """
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    return articles.length;
"""
article_count = driver.execute_script(count_js)
print(f"\n[4] Jumlah <article> tweet di halaman: {article_count}")

# Cek isi aria-label dari group pertama
debug_js = """
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    const results = [];
    for (let i = 0; i < Math.min(articles.length, 3); i++) {
        const article = articles[i];
        const info = {};
        
        // Content
        const textDiv = article.querySelector('div[data-testid="tweetText"]');
        info.content = textDiv ? textDiv.innerText.substring(0, 100) : 'NOT FOUND';
        
        // Author
        const userDiv = article.querySelector('div[data-testid="User-Name"]');
        info.author = userDiv ? userDiv.innerText.substring(0, 50) : 'NOT FOUND';
        
        // Group aria-label
        const group = article.querySelector('div[role="group"]');
        info.group_aria_label = group ? group.getAttribute('aria-label') : 'NOT FOUND';
        
        // Analytics link
        const analyticsLink = group ? group.querySelector('a[href*="/analytics"]') : null;
        info.analytics_link = analyticsLink ? (analyticsLink.getAttribute('aria-label') || analyticsLink.innerText) : 'NOT FOUND';
        
        // All buttons in group
        if (group) {
            const btns = group.querySelectorAll('button[data-testid]');
            info.buttons = [];
            btns.forEach(btn => {
                info.buttons.push({
                    testId: btn.getAttribute('data-testid'),
                    ariaLabel: btn.getAttribute('aria-label'),
                    text: btn.innerText
                });
            });
        }
        
        // Time
        const timeEl = article.querySelector('time');
        info.time = timeEl ? timeEl.getAttribute('datetime') : 'NOT FOUND';
        const timeLink = timeEl ? timeEl.closest('a') : null;
        info.url = timeLink ? timeLink.href : 'NOT FOUND';
        
        results.push(info);
    }
    return results;
"""

print("\n[5] Mengambil info diagnostik dari 3 tweet pertama...")
try:
    debug_data = driver.execute_script(debug_js)
    for i, d in enumerate(debug_data):
        print(f"\n  === Tweet #{i+1} ===")
        print(f"  Content: {d.get('content', 'N/A')}")
        print(f"  Author: {d.get('author', 'N/A')}")
        print(f"  Group aria-label: {d.get('group_aria_label', 'N/A')}")
        print(f"  Analytics link: {d.get('analytics_link', 'N/A')}")
        print(f"  Time: {d.get('time', 'N/A')}")
        print(f"  URL: {d.get('url', 'N/A')}")
        if d.get('buttons'):
            print(f"  Buttons ({len(d['buttons'])}):")
            for btn in d['buttons']:
                print(f"    - testId={btn['testId']}, aria={btn['ariaLabel']}, text={btn['text']}")
except Exception as e:
    print(f"  ERROR: {e}")

input("\nTekan Enter untuk menutup Chrome...")
driver.quit()
