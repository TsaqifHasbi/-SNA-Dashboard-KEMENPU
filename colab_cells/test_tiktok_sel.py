import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import json
import re

options = uc.ChromeOptions()
options.add_argument('--headless')
driver = uc.Chrome(options=options, version_main=153)
driver.get("https://www.tiktok.com/@jokowi/video/7373599981881675013")
time.sleep(5)
html = driver.page_source
driver.quit()

rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
if rehyd:
    data = json.loads(rehyd.group(1))
    default = data['__DEFAULT_SCOPE__']
    detail = default.get('webapp.video-detail', {})
    print("Detail Keys:", detail.keys())
    if 'itemInfo' in detail:
        print("itemStruct Keys:", detail['itemInfo'].get('itemStruct', {}).keys())
        stats = detail['itemInfo'].get('itemStruct', {}).get('stats', {})
        print("Stats:", stats)
    else:
        print("NO ITEM INFO")
        
soup = BeautifulSoup(html, 'html.parser')
like = soup.find(attrs={'data-e2e': 'like-count'})
print("BS4 Like:", like.text if like else "NONE")
