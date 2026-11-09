import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
import urllib.parse

def test_bing():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    driver = uc.Chrome(options=options)
    
    keyword = "makan bergizi gratis"
    query = f'site:instagram.com/p/ OR site:instagram.com/reel/ "{keyword}"'
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=50"
    
    driver.get(url)
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = soup.find_all('a', href=True)
    
    post_urls = []
    for link in links:
        href = link['href']
        # Bing kadang menyembunyikan link asli.
        if 'instagram.com/p/' in href or 'instagram.com/reel/' in href:
            if not href.startswith('/'):
                post_urls.append(href)
                
    print(f"Dapat {len(post_urls)} link IG unik:")
    for l in list(set(post_urls))[:10]:
        print(l)
        
    driver.quit()

if __name__ == '__main__':
    test_bing()
