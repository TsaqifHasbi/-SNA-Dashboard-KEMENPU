from duckduckgo_search import DDGS
query = '"makan bergizi gratis" site:instagram.com/p/'
results = []
try:
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=20):
            results.append(r['href'])
    print(f'Ditemukan {len(results)} links:')
    for link in results[:5]: print(link)
except Exception as e:
    print('Error:', e)
