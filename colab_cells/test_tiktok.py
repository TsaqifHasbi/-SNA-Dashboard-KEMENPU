import urllib.request
import re
import json

req = urllib.request.Request('https://www.tiktok.com/@jokowi/video/7373599981881675013', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req).read().decode('utf-8')
rehyd = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(rehyd.group(1))
default = data['__DEFAULT_SCOPE__']
detail = default.get('webapp.video-detail', {})
print('Detail keys:', detail.keys())
print('itemInfo keys:', detail.get('itemInfo', {}).keys())
print('itemStruct keys:', detail.get('itemInfo', {}).get('itemStruct', {}).keys())
