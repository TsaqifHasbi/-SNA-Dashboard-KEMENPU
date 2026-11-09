import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
import urllib.parse

def test_google():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    
    keyword = "makan bergizi gratis"
    query = f'site:instagram.com/p/ OR site:instagram.com/reel/ "{keyword}"'
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=100"
    
    driver.get(url)
    print("Membuka Google. Tolong selesaikan Captcha jika ada (tunggu 10 detik)...")
    time.sleep(15)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'instagram.com/p/' in href or 'instagram.com/reel/' in href:
            links.append(href)
            
    print(f"Dapat {len(links)} link IG unik:")
    for l in list(set(links))[:5]:
        print(l)
        
    driver.quit()

if __name__ == '__main__':
    test_google()
