import undetected_chromedriver as uc
import time, json, re

options = uc.ChromeOptions()
# options.add_argument('--headless')
driver = uc.Chrome(options=options, version_main=153)
driver.get('https://www.tiktok.com/')
time.sleep(5) # wait for load

html = driver.execute_async_script("""
var url = 'https://www.tiktok.com/@jokowi/video/7373599981881675013';
var callback = arguments[0];
fetch(url).then(r => r.text()).then(t => callback(t)).catch(e => callback('ERR: ' + e));
""")
driver.quit()

rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
if rehyd:
    print("Found rehyd!")
    data = json.loads(rehyd.group(1))
    default = data.get('__DEFAULT_SCOPE__', {})
    detail = default.get('webapp.video-detail', {})
    if 'itemInfo' in detail:
        stats = detail['itemInfo'].get('itemStruct', {}).get('stats', {})
        print("Stats:", stats)
else:
    print("Not found. HTML length:", len(html))
    print(html[:200])
