import undetected_chromedriver as uc
import time, json, re

options = uc.ChromeOptions()
options.add_argument('--headless')
driver = uc.Chrome(options=options, version_main=153)
driver.get('https://www.tiktok.com/search?q=jokowi')
time.sleep(5)
html = driver.page_source
driver.quit()

rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
if rehyd:
    data = json.loads(rehyd.group(1))
    print('Found rehyd')
    default = data.get('__DEFAULT_SCOPE__', {})
    search = default.get('webapp.search-index', {})
    if not search:
        # maybe it's under something else?
        for k in default.keys():
            print("DEFAULT KEY:", k)
    else:
        print('search keys:', search.keys())
        if 'itemInfoList' in search:
            print('itemInfoList found, len:', len(search['itemInfoList']))
            if len(search['itemInfoList']) > 0:
                print('Sample keys:', search['itemInfoList'][0].keys())
        if 'itemModule' in search:
             print('itemModule found')
