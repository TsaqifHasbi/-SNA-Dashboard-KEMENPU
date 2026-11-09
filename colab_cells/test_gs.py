import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GRAMSCRAPER_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}"
}

# Coba ambil hashtag medias recent
url = "https://gramscraper.com/api/instagram/v2/hashtag/medias/recent?name=makanbergizigratis"
print(f"Mengakses: {url}")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Keys di JSON:", data.keys())
    
    # Biasanya data post ada di key 'response'
    items = data.get('response', [])
    print(f"Tipe items: {type(items)}")
    
    if isinstance(items, dict) and 'sections' in items:
        all_posts = []
        for section in items['sections']:
            layout = section.get('layout_content', {})
            medias = layout.get('medias', [])
            for m in medias:
                if 'media' in m:
                    all_posts.append(m['media'])
        
        print(f"Total post ditemukan di halaman pertama: {len(all_posts)}")
        if all_posts:
            p = all_posts[0]
            print("\n=== POST PERTAMA ===")
            print(f"ID: {p.get('id')}")
            print(f"URL/Code: https://instagram.com/p/{p.get('code')}/")
            
            user = p.get('user', {})
            print(f"Username: {user.get('username')}")
            
            caption = p.get('caption', {})
            if caption:
                text = caption.get('text', '')
                print(f"Caption: {text[:100]}...")
            
            print(f"Likes: {p.get('like_count')}")
            print(f"Comments: {p.get('comment_count')}")
