import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
import urllib.parse

def test_ddg():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    driver = uc.Chrome(options=options)
    
    keyword = "makan bergizi gratis"
    query = f'site:instagram.com/p/ OR site:instagram.com/reel/ "{keyword}"'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    driver.get(url)
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = soup.find_all('a', class_='result__url')
    
    post_urls = []
    for link in links:
        href = link.get('href', '')
        if 'instagram.com/p/' in href or 'instagram.com/reel/' in href:
            if href.startswith('//'):
                href = 'https:' + href
            post_urls.append(href)
            
    print(f"Dapat {len(post_urls)} link IG unik:")
    for l in list(set(post_urls))[:5]:
        print(l)
        
    driver.quit()

if __name__ == '__main__':
    test_ddg()
