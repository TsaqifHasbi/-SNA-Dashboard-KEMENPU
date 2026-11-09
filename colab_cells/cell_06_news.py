from cell_02_config import *
# ============================================================
# CELL 6: SCRAPER NEWS (Google News RSS + Bing News RSS)
# Tools: feedparser (Ringan, Cepat, Bebas Rate-Limit)
# Target: ~16.000 artikel
# ============================================================

from datetime import datetime, timedelta, timezone
import time
import re
import html
import urllib.parse
# pyrefly: ignore [missing-import]
import feedparser

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

def _parse_date_to_wib(date_str):
    """Parse tanggal dari RSS feed dan konversi ke WIB."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        dt_wib = dt.astimezone(WIB)
        return dt_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
    except:
        pass
    
    # Fallback: coba format umum
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_wib = dt.astimezone(WIB)
            return dt_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
        except:
            continue
    
    return date_str


def _clean_title(title, pub_name=""):
    """Bersihkan judul dari nama publisher yang menempel di akhir."""
    if not title:
        return title
    # Hapus " - Publisher" di akhir judul
    if pub_name and title.endswith(f" - {pub_name}"):
        title = title[: -(len(f" - {pub_name}"))].strip()
    elif " - " in title:
        parts = title.rsplit(" - ", 1)
        # Hanya hapus jika bagian terakhir pendek (nama publisher)
        if len(parts) > 1 and len(parts[1]) < 50:
            title = parts[0].strip()
    return title


def _scrape_google_news(keyword, max_results=100):
    """Scrape dari Google News RSS Feed."""
    results = []
    seen_urls = set()

    try:
        q_text = keyword
        since_env = os.environ.get('SCRAPE_SINCE')
        until_env = os.environ.get('SCRAPE_UNTIL')
        if since_env and 'after:' not in q_text:
            q_text += f" after:{since_env} before:{until_env}"
        query = urllib.parse.quote(q_text)
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
        
        feed = feedparser.parse(rss_url)
        
        for idx, entry in enumerate(feed.entries):
            url = entry.get("link", "")
            title = entry.get("title", "")
            
            if url in seen_urls or not title:
                continue
            seen_urls.add(url)
            
            # Ambil nama publisher
            pub_name = ""
            source_obj = getattr(entry, "source", None)
            if source_obj and hasattr(source_obj, "get"):
                pub_name = source_obj.get("title", "")
            elif isinstance(source_obj, dict):
                pub_name = source_obj.get("title", "")
            
            if not pub_name and " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) > 1 and len(parts[1]) < 50:
                    pub_name = parts[1].strip()
            
            if not pub_name:
                pub_name = "Berita Online"
            
            # Bersihkan judul
            clean = _clean_title(title, pub_name)
            
            # Handle
            handle_name = f"@{pub_name.lower().replace(' ', '').replace('.', '_')}"
            
            # Parse tanggal ke WIB
            raw_date = entry.get("published", "")
            created_at = _parse_date_to_wib(raw_date) if raw_date else datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
            
            # FILTER TANGGAL: Mendukung filter tanggal spesifik jika SCRAPE_SINCE aktif
            if since_env and created_at < f"{since_env} 00:00:00 WIB":
                continue
            elif not since_env and created_at < "2024-01-01 00:00:00 WIB":
                continue
            
            # Bersihkan summary
            summary = entry.get("summary", "")
            summary = re.sub(r'<[^>]+>', '', summary).strip()
            summary = html.unescape(summary)
            
            results.append({
                "post_id": f"news_google_{idx}_{abs(hash(url)) % 1000000}",
                "platform": "News",
                "source": "Google News",
                "author": pub_name,
                "handle": handle_name,
                "content": clean,
                "description": summary[:1000] if summary else "",
                "created_at": created_at,
                "url": url,
                "keyword": keyword,
                "scraped_at": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
            })
            
    except Exception as e:
        print(f"      [!] Google News error: {str(e)[:80]}")

    return results


def _scrape_bing_news(keyword, max_results=100):
    """Scrape dari Bing News RSS Feed."""
    results = []
    seen_urls = set()

    try:
        query = urllib.parse.quote(keyword)
        # Bing News RSS - format=rss, cc=ID untuk Indonesia
        rss_url = f"https://www.bing.com/news/search?q={query}&format=rss&cc=ID&setlang=id"
        
        feed = feedparser.parse(rss_url)
        
        for idx, entry in enumerate(feed.entries):
            url = entry.get("link", "")
            title = entry.get("title", "")
            
            if url in seen_urls or not title:
                continue
            seen_urls.add(url)
            
            # Publisher dari news_source (khusus Bing) atau title
            pub_name = entry.get("news_source", "")
            
            if not pub_name and " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) > 1 and len(parts[1]) < 50:
                    pub_name = parts[1].strip()
            
            if not pub_name:
                pub_name = "Berita Online"
            
            # Bersihkan judul
            clean = _clean_title(title, pub_name)
            
            # Handle
            handle_name = f"@{pub_name.lower().replace(' ', '').replace('.', '_')}"
            
            # Parse tanggal ke WIB
            raw_date = entry.get("published", "")
            created_at = _parse_date_to_wib(raw_date) if raw_date else datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
            
            # FILTER TANGGAL: Mendukung filter tanggal spesifik jika SCRAPE_SINCE aktif
            if since_env and created_at < f"{since_env} 00:00:00 WIB":
                continue
            elif not since_env and created_at < "2024-01-01 00:00:00 WIB":
                continue
            
            # Description
            summary = entry.get("summary", entry.get("description", ""))
            summary = re.sub(r'<[^>]+>', '', summary).strip()
            summary = html.unescape(summary)
            
            results.append({
                "post_id": f"news_bing_{idx}_{abs(hash(url)) % 1000000}",
                "platform": "News",
                "source": "Bing News",
                "author": pub_name,
                "handle": handle_name,
                "content": clean,
                "description": summary[:1000] if summary else "",
                "created_at": created_at,
                "url": url,
                "keyword": keyword,
                "scraped_at": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
            })
            
    except Exception as e:
        print(f"      [!] Bing News error: {str(e)[:80]}")

    return results


def scrape_news(keyword, max_results=100):
    """
    Scrape berita dari Google News RSS + Bing News RSS dengan ekspansi
    portal dan rentang tanggal jika target kuota > 100 data.
    """
    seen = set()
    unique = []

    def _add_entries(entries):
        nonlocal unique
        for r in entries:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u)
                unique.append(r)
                if len(unique) >= max_results:
                    return True
        return False

    # 1. PENCARIAN DASAR (Google News + Bing News)
    base_google = _scrape_google_news(keyword, max_results=min(max_results, 100))
    if _add_entries(base_google):
        return unique

    base_bing = _scrape_bing_news(keyword, max_results=min(max_results, 100))
    if _add_entries(base_bing):
        return unique

    # Jika target <= 100 atau kuota sudah terpenuhi, kembalikan langsung
    if len(unique) >= max_results or max_results <= 100:
        return unique

    # 2. EKSPANSI VIA MEDIA PORTAL NASIONAL & OTOMOTIF UTAMA
    portals = [
        "kompas.com", "detik.com", "tempo.co", "kumparan.com", "liputan6.com",
        "antaranews.com", "cnnindonesia.com", "cnbcindonesia.com", "bisnis.com",
        "tribunnews.com", "gridoto.com", "oto.detik.com", "suara.com", "jawapos.com",
        "sindonews.com", "republika.co.id", "katadata.co.id", "kontan.co.id",
        "otodriver.com", "viva.co.id", "merdeka.com", "idntimes.com", "tirto.id",
        "medcom.id", "okezone.com", "inews.id", "beritasatu.com", "disway.id"
    ]

    for p in portals:
        portal_query = f"{keyword} site:{p}"
        portal_results = _scrape_google_news(portal_query, max_results=100)
        if _add_entries(portal_results):
            return unique
        time.sleep(0.15)

    if len(unique) >= max_results:
        return unique

    # 3. EKSPANSI RENTANG TANGGAL (Time Window Slicing 2024 - 2026)
    date_windows = [
        ("2024-01-01", "2024-04-30"), ("2024-05-01", "2024-08-31"), ("2024-09-01", "2024-12-31"),
        ("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"), ("2025-07-01", "2025-09-30"),
        ("2025-10-01", "2025-12-31"), ("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-30"),
        ("2026-07-01", "2026-10-31"), ("2026-11-01", "2026-12-31")
    ]

    for start_d, end_d in date_windows:
        date_query = f"{keyword} after:{start_d} before:{end_d}"
        date_results = _scrape_google_news(date_query, max_results=100)
        if _add_entries(date_results):
            return unique
        time.sleep(0.15)

    # 4. EKSPANSI BING PAGINATION
    for offset in range(11, 200, 20):
        try:
            q_enc = urllib.parse.quote(keyword)
            rss_url = f"https://www.bing.com/news/search?q={q_enc}&format=rss&cc=ID&setlang=id&first={offset}"
            feed = feedparser.parse(rss_url)
            bing_page = []
            for idx, entry in enumerate(feed.entries):
                u = entry.get("link", "")
                t = entry.get("title", "")
                if not u or not t: continue
                clean = _clean_title(t)
                created_at = _parse_date_to_wib(entry.get("published", ""))
                bing_page.append({
                    "post_id": f"news_bing_p_{offset}_{idx}_{abs(hash(u)) % 1000000}",
                    "platform": "News",
                    "source": "Bing News",
                    "author": entry.get("news_source", "Berita Online"),
                    "handle": "@beritaonline",
                    "content": clean,
                    "description": entry.get("summary", "")[:1000],
                    "created_at": created_at,
                    "url": u,
                    "keyword": keyword,
                    "scraped_at": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
                })
            if _add_entries(bing_page):
                return unique
            time.sleep(0.15)
        except Exception:
            pass

    return unique


# ============================================================
# KEYWORD EKSPANSI OTOMATIS UNTUK NEWS (DIKOSONGKAN AGAR TETAP FOKUS 5 KEYWORD)
# ============================================================
NEWS_EXTRA_KEYWORDS = {}


# ============================================================
# TEST (hanya jika dijalankan langsung)
# ============================================================
if __name__ == "__main__":
    print("[TEST] Menguji News scraper (Google + Bing)...")
    test = scrape_news("Kementerian Pekerjaan Umum", max_results=5)
    print(f"[OK] News: {len(test)} artikel ditemukan")
    for t in test:
        src = t.get('source', '?')
        print(f"   [{src}] {t['content'][:60]}...")
        print(f"      Publisher: {t['author']} | Handle: {t['handle']} | Tanggal: {t['created_at']}")
