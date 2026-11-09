from duckduckgo_search import DDGS

query = 'site:instagram.com "makan bergizi gratis"'
results = []
try:
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=50):
            if 'instagram.com/p/' in r['href'] or 'instagram.com/reel/' in r['href']:
                results.append(r['href'])
    print(f'Ditemukan {len(results)} links:')
    for link in results[:5]: print(link)
except Exception as e:
    print('Error:', e)
