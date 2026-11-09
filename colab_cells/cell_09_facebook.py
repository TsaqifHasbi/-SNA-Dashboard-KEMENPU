# ============================================================
# CELL 9: SCRAPING FACEBOOK (SELENIUM UNDETECTED)
# ============================================================
import time
import os
import sys
import re
import random
import shutil
import urllib.parse
from datetime import datetime, timezone, timedelta
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

WIB = timezone(timedelta(hours=7))

FB_PROFILE_DIR = os.path.join(os.path.expanduser('~'), '.facebook_scraper_profile')
os.makedirs(FB_PROFILE_DIR, exist_ok=True)

try:
    from cell_02_config import detect_topic, is_relevant_topic
except ImportError:
    detect_topic = None
    is_relevant_topic = None

_SEEN_URLS = set()

def load_seen_urls(urls):
    """Memuat URL yang sudah ada dari CSV agar tidak di-scrape ulang."""
    global _SEEN_URLS
    if urls:
        _SEEN_URLS.update(urls)
        print(f"    [DEDUP] {len(_SEEN_URLS)} URL Facebook dimuat untuk deduplikasi global.")

def reset_tracking():
    """Reset URL tracking."""
    global _SEEN_URLS
    _SEEN_URLS = set()

def parse_eng(text):
    if not text: return '0'
    text = text.lower().replace(' ', '')
    m = re.search(r'([\d\.,]+)([kmrbjtribuja]*)', text)
    if not m: return '0'
    
    num_str = m.group(1).replace(',', '.')
    try:
        num = float(num_str)
    except:
        return '0'
        
    suffix = m.group(2)
    if 'k' in suffix or 'rb' in suffix or 'ribu' in suffix:
        num *= 1000
    elif 'm' in suffix or 'jt' in suffix or 'juta' in suffix:
        num *= 1000000
        
    return str(int(num))


try:
    # pyrefly: ignore [missing-import]
    import undetected_chromedriver as uc
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.common.by import By
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.common.keys import Keys
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.common.action_chains import ActionChains
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.support.ui import WebDriverWait
    # pyrefly: ignore [missing-import]
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    pass

FB_DRIVER = None
FB_SEARCH_TAB = None
FB_WORKER_TAB = None


def _clean_text(text):
    """Membersihkan teks dari artefak UI Facebook, teks ter-obfuscate, dan karakter baris baru."""
    if not text:
        return ""
    # Hapus karakter obfuscation U+034F (combining grapheme joiner khas timestamp/sponsored Facebook)
    if text.count('\u034f') > 2:
        return ""
    text = text.replace('\u034f', '')
    
    # Hapus tombol-tombol UI
    for junk in ['See less', 'See more', 'See Less', 'See More',
                 'Lihat selengkapnya', 'Selengkapnya', 'selengkapnya', 'Sembunyikan',
                 'See translation', 'See Translation',
                 'Lihat Terjemahan', 'Translated by Meta AI']:
        text = text.replace(junk, '')
    
    # Ganti newline dan carriage return menjadi spasi agar tidak merusak format CSV
    text = re.sub(r'[\r\n\u2028\u2029]+', ' ', text)
    # Collapse spasi berlebih
    text = re.sub(r' +', ' ', text).strip()
    
    # Buang teks jika hanya berisi metadata AI atau timestamp sampah
    if re.search(r'^(?:AI content\s*·?\s*|Sponsored\s*·?\s*|[·\s\d:\.\/apmAPM,-]+)$', text):
        return ""
    return text


def _clean_engagement(raw):
    """Membersihkan string angka engagement dan mengkonversi ke nominal asli."""
    if not raw:
        return "0"
    raw = raw.strip()
    # Mengonversi teks seperti "27K" menjadi "27000" sesuai permintaan user
    return parse_eng(raw)


def _extract_via_js(driver):
    """
    Menggunakan JavaScript untuk mengekstrak data post langsung dari DOM.
    Ini JAUH lebih akurat daripada BeautifulSoup karena bisa membaca
    elemen yang sudah di-render oleh React/JS Facebook.
    """
    script = r"""
    // Cari semua elemen post. Di Facebook Search, feed ada di div[role="feed"]
    let posts = [];
    
    // Strategi 1: Direct children dari div[role="feed"]
    let feed = document.querySelector('div[role="feed"]');
    let articles = [];
    if (feed) {
        articles = Array.from(feed.children).filter(c => {
            return c.querySelectorAll('a[href]').length > 0 && (c.innerText || '').length > 30;
        });
    }
    
    // Strategi 2: div[role="article"]
    if (articles.length === 0) {
        articles = Array.from(document.querySelectorAll('div[role="article"]'));
    }
    
    // Strategi 3: Fallback cari heading h2, h3, h4 lalu panjat ke atas
    if (articles.length === 0) {
        let headers = document.querySelectorAll('h3, h4');
        let containers = new Set();
        headers.forEach(h => {
            let p = h;
            for (let i = 0; i < 8; i++) {
                if (p.parentElement) p = p.parentElement;
            }
            containers.add(p);
        });
        articles = Array.from(containers);
    }
    
    for (let article of articles) {
        let post = {};
        
        // 1. AUTHOR: Cari dari header artikel agar tidak salah menangkap nama grup
        let headerDiv = article.querySelector('div[data-ad-preview="message"]')?.parentElement?.previousElementSibling || article;
        let headerLinks = Array.from(headerDiv.querySelectorAll('h2 a[role="link"], h3 a[role="link"], h4 a[role="link"], a[role="link"], a[tabindex="0"]'))
            .filter(a => a.innerText.trim().length > 0 && !/(like|comment|share|follow|bergabung|suka|komentar|bagikan)/i.test(a.innerText));
        
        // Helper untuk membersihkan nama dan filter kata-kata sampah UI
        let isJunkAuthor = (name) => {
            if (!name || name.trim().length < 2) return true;
            let lower = name.toLowerCase().replace(/[\r\n]+/g, ' ').trim();
            if (/(online status indicator|active|aktif)/i.test(lower)) return true;
            let junkWords = [
                'see more', 'see less', 'lihat selengkapnya', 'selengkapnya', 'sembunyikan',
                'online status indicator', 'active', 'aktif', 'follow', 'ikuti', 'join', 'gabung',
                'bagikan', 'share', 'suka', 'like', 'komentar', 'comment', 'kirim', 'send',
                'original text', 'lihat teks asli', 'lihat yang asli', 'translated by', 'terjemahan',
                'foto', 'video', 'grup', 'komunitas'
            ];
            return junkWords.some(j => lower === j || lower.startsWith(j + ' ') || lower.endsWith(' ' + j));
        };

        let extractCleanName = (txt) => {
            if (!txt) return '';
            let lines = txt.split(/[\r\n]+/).map(l => l.trim()).filter(l => l.length > 0);
            let valid = lines.filter(l => !/(Online status indicator|Active|Aktif)/i.test(l));
            return valid.length > 0 ? valid[0].replace(/[\r\n]+/g, ' ').trim() : '';
        };

        post.author = '';
        if (headerLinks.length > 0) {
            let candidate = extractCleanName(headerLinks[0].innerText);
            if (!isJunkAuthor(candidate)) {
                post.author = candidate;
            }
            if (headerLinks[0].href.includes('/groups/') && headerLinks.length > 1) {
                let altName = extractCleanName(headerLinks[1].innerText);
                if (altName && !isJunkAuthor(altName)) post.author = altName;
            }
        }
        
        // Fallback jika tidak ditemukan
        if (!post.author) {
            let authorEls = article.querySelectorAll('h2, h3, h4');
            for (let el of authorEls) {
                let name = extractCleanName(el.innerText);
                if (name && !isJunkAuthor(name)) {
                    post.author = name;
                    break;
                }
            }
        }
        
        // Skip jika author kosong atau sampah
        if (post.author.length < 2 || isJunkAuthor(post.author)) continue;
        
        // 2. CONTENT: Ambil teks postingan utama yang sudah di-expand
        let textDivs = Array.from(article.querySelectorAll('div[dir="auto"], span[dir="auto"]'))
            .filter(d => !d.closest('a') && !d.closest('h2, h3, h4') && !d.closest('div[role="toolbar"]') && !d.closest('form'))
            .map(d => (d.innerText || '').trim())
            .filter(t => t.length > 15 && 
                         !t.includes('\\u034f') &&
                         !/^(Komentar|Bagikan|Suka|Like|Comment|Share|Kirim|Send|Write a comment|Tulis komentar|Lihat komentar|Balas)/i.test(t) &&
                         !(/^(?:AI content|Sponsored|Bersponsor)/i.test(t) && t.length < 50) &&
                         !t.startsWith('http'));

        // Urutkan untuk mendapatkan teks postingan utama yang paling lengkap
        textDivs.sort((a, b) => b.length - a.length);
        post.content = textDivs.length > 0 ? textDivs[0] : '';
        
        // Skip jika content kosong
        if (post.content.length < 20) continue;
        
        // 3. URL: RESOLUSI PERMALINK POSTINGAN RESMI (STRICT: NO STORIES, NO COMMUNITY ROOTS)
        let allLinks = Array.from(article.querySelectorAll('a[href]'))
            .map(a => a.getAttribute('href') || '')
            .filter(href => {
                if (!href || href === '#' || href.startsWith('javascript:')) return false;
                // STRICT DROP: Stories (konten 24 jam sementara)
                if (href.includes('/stories/')) return false;
                // STRICT DROP: Share dialogs, hovercards, hashtags, search
                if (href.includes('dialog/share') || href.includes('sharer.php') || href.includes('hovercard') || href.includes('hashtag/') || href.includes('/groups/search/')) return false;
                return true;
            });

        let bestLink = null;

        // A. Cek direct group post: /groups/<id>/posts/<id> atau /groups/<id>/permalink/<id>
        for (let l of allLinks) {
            if (/\/groups\/[^/?]+\/(?:posts|permalink)\/\d+/.test(l)) {
                bestLink = l.split('?')[0];
                break;
            }
        }

        // B. Cek direct user post: /<user>/posts/<id> atau /permalink.php?story_fbid=
        if (!bestLink) {
            for (let l of allLinks) {
                if (/\/posts\/(?:pfbid|\d+)/.test(l) && !l.includes('/groups/')) {
                    bestLink = l.split('?')[0];
                    break;
                }
                if (l.includes('permalink.php') && l.includes('story_fbid=')) {
                    bestLink = l.split('&__cft__')[0].split('?__cft__')[0];
                    break;
                }
            }
        }

        // C. Cek video / reel / watch
        if (!bestLink) {
            for (let l of allLinks) {
                if (l.includes('/reel/') || l.includes('/videos/') || l.includes('/watch/')) {
                    bestLink = l.split('?')[0];
                    break;
                }
            }
        }

        // D. Rekonstruksi dari photo jika ada parameter set=gm (Group post) atau set=pcb (Profile post)
        if (!bestLink) {
            for (let l of allLinks) {
                if (l.includes('/photo') || l.includes('fbid=')) {
                    // Cek set=gm.<post_id>&idorvanity=<group_id>
                    let m_gm = l.match(/set=gm\.(\d+)/);
                    let m_grp = l.match(/idorvanity=(\d+)/);
                    if (m_gm && m_grp) {
                        bestLink = `/groups/${m_grp[1]}/posts/${m_gm[1]}/`;
                        break;
                    } else if (m_gm) {
                        for (let other of allLinks) {
                            let m_other = other.match(/\/groups\/(\d+)/);
                            if (m_other) {
                                bestLink = `/groups/${m_other[1]}/posts/${m_gm[1]}/`;
                                break;
                            }
                        }
                        if (bestLink) break;
                    }

                    // Cek set=pcb.<post_id>
                    let m_pcb = l.match(/set=pcb\.(\d+)/);
                    if (m_pcb) {
                        let author_id = null;
                        for (let other of allLinks) {
                            let m_u = other.match(/profile\.php\?id=(\d+)/);
                            if (m_u) { author_id = m_u[1]; break; }
                            let m_u2 = other.match(/facebook\.com\/([^/?]+)/);
                            if (m_u2 && !['photo', 'groups', 'pages', 'watch', 'reel'].includes(m_u2[1])) {
                                author_id = m_u2[1];
                                break;
                            }
                        }
                        if (author_id) {
                            bestLink = `/${author_id}/posts/${m_pcb[1]}/`;
                            break;
                        } else {
                            let fbidMatch = l.match(/fbid=(\d+)/);
                            if (fbidMatch) {
                                bestLink = `/photo/?fbid=${fbidMatch[1]}&set=pcb.${m_pcb[1]}`;
                                break;
                            }
                        }
                    }

                    // Fallback photo permalink bersih
                    let fbidM = l.match(/fbid=(\d+)/);
                    if (fbidM) {
                        bestLink = `/photo/?fbid=${fbidM[1]}`;
                        break;
                    }
                }
            }
        }

        // STRICT FILTER: JANGAN PERNAH SIMPAN ROOT GROUP (/groups/123/) ATAU ROOT PROFILE ATAU STORY
        if (!bestLink) continue;
        if (bestLink.includes('/stories/')) continue;
        if (/^\/groups\/\d+\/?$/.test(bestLink) || /^\/groups\/[^/?]+\/?$/.test(bestLink)) continue;
        if (bestLink === '/' || bestLink === 'https://www.facebook.com/' || bestLink.includes('/search/')) continue;

        if (!bestLink.startsWith('http')) {
            bestLink = 'https://www.facebook.com' + bestLink;
        }
        post.url = bestLink;
        
        // 4. ENGAGEMENT: Cari dari aria-label dan DOM traverse
        post.likes = '0';
        post.comments = '0';
        post.shares = '0';
        
        // Metode A: Cari elemen dengan aria-label
        let allEls = article.querySelectorAll('*[aria-label]');
        for (let el of allEls) {
            let label = el.getAttribute('aria-label').toLowerCase();
            let numMatch = label.match(/([\\.\\d,]+\\s*(?:k|m|rb|ribu|jt|juta)?)/i);
            if (!numMatch) continue;
            let numStr = numMatch[1];
            
            if (/(suka|like|reaksi|reaction)/i.test(label)) {
                if (post.likes === '0') post.likes = numStr;
            } else if (/(komentar|comment)/i.test(label)) {
                if (post.comments === '0') post.comments = numStr;
            } else if (/(bagikan|share)/i.test(label)) {
                if (post.shares === '0') post.shares = numStr;
            }
        }
        
        // Metode B: Traverse langsung pada Action Row untuk menangkap teks div/span
        let likeBtn = Array.from(article.querySelectorAll('div[role="button"], div[tabindex="0"], span')).find(b => /^(Like|Suka)$/i.test(b.innerText?.trim()));
        if (likeBtn) {
            // Container Action Toolbar biasanya ada 2-3 level di atas Like
            let actionRow = likeBtn.closest('div.x1n2onr6, div.x1y1aw1k') || likeBtn.parentElement.parentElement;
            // Baris angka engagement biasanya adalah previous sibling dari Action Toolbar
            let engagementRow = actionRow ? actionRow.previousElementSibling : null;
            
            if (engagementRow) {
                let text = engagementRow.innerText || '';
                
                // Cek eksplisit dengan indikator
                let cm = text.match(/([\\.\\d,]+\\s*(?:k|m|rb|ribu|jt|juta)?)\\s*(comments?|komentar)/i);
                if (cm && post.comments === '0') post.comments = cm[1];
                
                let sm = text.match(/([\\.\\d,]+\\s*(?:k|m|rb|ribu|jt|juta)?)\\s*(shares?|kali dibagikan|bagikan)/i);
                if (sm && post.shares === '0') post.shares = sm[1];
                
                // Ambil semua token angka bebas yang ada (dipisahkan spasi atau newline)
                let tokens = text.split(/[\\n\\s]+/);
                let nums = tokens.filter(t => /^[\\.\\d,]+(?:k|m|rb|ribu|jt|juta)?$/i.test(t));
                nums = [...new Set(nums)]; // Hapus duplikat
                
                // Assign sisa angka bebas secara berurutan: likes, comments, shares
                if (post.likes === '0' && nums.length >= 1) post.likes = nums[0];
                if (post.comments === '0' && nums.length >= 2) post.comments = nums[1];
                if (post.shares === '0' && nums.length >= 3) post.shares = nums[2];
            }
        }
        
        // Metode C: Teks langsung regex keseluruhan (sebagai fallback terakhir)
        let fullText = article.innerText;
        if (post.likes === '0') {
            let m = fullText.match(/([\\.\\d,]+\\s*(?:K|M|rb|ribu|jt|juta)?)\\s*(?:suka|like|reaksi|people like this)/i);
            if (m) post.likes = m[1];
        }
        if (post.comments === '0') {
            let m = fullText.match(/([\\.\\d,]+\\s*(?:K|M|rb|ribu|jt|juta)?)\\s*(?:komentar|comments?)/i);
            if (m) post.comments = m[1];
        }
        if (post.shares === '0') {
            let m = fullText.match(/([\\.\\d,]+\\s*(?:K|M|rb|ribu|jt|juta)?)\\s*(?:kali dibagikan|shares?|bagikan)/i);
            if (m) post.shares = m[1];
        }
        
        // Metode D: Trailing Numbers (Menangkap UI FB Baru yang hanya ikon tanpa teks label)
        let ignoreRegex = /^(Like|Suka|Comment|Komentar|Share|Bagikan|Send|Kirim|See more|Lihat selengkapnya|See translation|Lihat terjemahan|Original text|Lihat teks asli|Hide|Sembunyikan|Write a comment|Tulis komentar.*)$/i;
        let lines = (article.innerText || '').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        let trailingNums = [];
        for (let i = lines.length - 1; i >= 0; i--) {
            let line = lines[i];
            // Jika baris berisi angka murni (termasuk k, rb, jt) dan panjangnya logis
            if (/^[\\.\\d,]+\\s*(?:k|m|rb|ribu|jt|juta)?$/i.test(line) && line.length <= 12) {
                trailingNums.unshift(line);
            } else if (!ignoreRegex.test(line)) {
                // Berhenti mencari jika menemukan teks normal
                break;
            }
        }
        // Metode E: Multiline Number Tokens (misal "58\n32" atau "42\n12")
        let engTokens = [];
        article.querySelectorAll('div, span').forEach(el => {
            let t = (el.innerText || '').trim();
            if (/^\d+\s*[\n\r]\s*\d+(?:\s*[\n\r]\s*\d+)?$/.test(t)) {
                let parts = t.split(/[\n\r\s]+/).filter(x => /^\d+$/.test(x));
                if (parts.length > engTokens.length) engTokens = parts;
            }
        });
        if (engTokens.length >= 1 && post.likes === '0') post.likes = engTokens[0];
        if (engTokens.length >= 2 && (post.comments === '0' || post.comments === 0)) post.comments = engTokens[1];
        if (engTokens.length >= 3 && (post.shares === '0' || post.shares === 0)) post.shares = engTokens[2];
        
        posts.push(post);
    }
    
    return posts;
    """
    try:
        return driver.execute_script(script)
    except Exception as e:
        print(f"    [WARN] JS extraction failed: {e}")
        return []


def _get_chrome_major_version():
    """Deteksi versi major Chrome dari Windows Registry secara dinamis."""
    try:
        import winreg
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                key = winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon")
                v, _ = winreg.QueryValueEx(key, "version")
                if v and '.' in v:
                    return int(v.split('.')[0])
            except Exception:
                pass
    except Exception:
        pass
    return None


def _build_chrome_options():
    """Membuat instance ChromeOptions baru setiap pemanggilan agar tidak terkena error reuse."""
    options = uc.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.add_argument("--disable-notifications")
    options.add_argument('--lang=id-ID,id,en-US,en')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,ThrottleDisplayNoneAndDisplayInlineCSS')
    options.add_argument(f'--user-data-dir={FB_PROFILE_DIR}')
    return options


def _init_driver(skip_input=False):
    """Buat driver Facebook dengan profile persisten."""
    global FB_DRIVER

    if FB_DRIVER is not None:
        try:
            FB_DRIVER.quit()
        except:
            pass
        FB_DRIVER = None

    major_v = _get_chrome_major_version()
    driver_started = False

    if major_v:
        try:
            FB_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=major_v)
            driver_started = True
        except Exception:
            time.sleep(1)

    if not driver_started:
        try:
            FB_DRIVER = uc.Chrome(options=_build_chrome_options())
            driver_started = True
        except Exception:
            time.sleep(1)

    if not driver_started and major_v:
        for fallback_v in [major_v - 1, major_v - 2]:
            try:
                FB_DRIVER = uc.Chrome(options=_build_chrome_options(), version_main=fallback_v)
                driver_started = True
                break
            except Exception:
                pass

    if not driver_started or FB_DRIVER is None:
        raise RuntimeError("Gagal membuka Chrome Selenium. Pastikan Chrome tidak diblokir oleh proses lain.")

    # Cek apakah sesi login Facebook sudah aktif di profile
    FB_DRIVER.get("https://www.facebook.com/")
    print("    [INFO] Membuka Facebook di Chrome...")
    time.sleep(3)

    is_logged_in = False
    try:
        is_logged_in = FB_DRIVER.execute_script("""
            return !document.querySelector('input[name="email"]') && 
                   !document.querySelector('button[name="login"]') &&
                   (!!document.querySelector('div[role="navigation"]') || !!document.querySelector('svg[aria-label="Your profile"]'));
        """)
    except:
        pass

    if not is_logged_in and not skip_input:
        print("\n" + "="*60)
        print("🔐 SILAKAN LOGIN KE AKUN FACEBOOK ANDA DI BROWSER 🔐")
        print("1. Jendela Chrome sudah terbuka di https://www.facebook.com/")
        print("2. Silakan login ke akun Facebook Anda (Gunakan akun baru/cadangan).")
        print("3. Selesaikan 2FA / verifikasi jika diminta.")
        print("4. Pastikan Anda sudah masuk ke Beranda Facebook.")
        print("="*60 + "\n")
        if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
            try:
                input("👉 TEKAN ENTER DI SINI JIKA SUDAH BERHASIL MASUK KE BERANDA FB... ")
            except (EOFError, KeyboardInterrupt):
                pass
            print("    [OK] Melanjutkan ke proses pencarian...")
            time.sleep(2)
        else:
            print("    [INFO] Menunggu Anda login di browser (maksimal 120 detik)...")
            for _ in range(40):
                time.sleep(3)
                try:
                    check_in = FB_DRIVER.execute_script("""
                        return !document.querySelector('input[name="email"]') && 
                               !document.querySelector('button[name="login"]') &&
                               (!!document.querySelector('div[role="navigation"]') || !!document.querySelector('svg[aria-label="Your profile"]'));
                    """)
                    if check_in:
                        print("    [OK] Sesi login Facebook aktif ditemukan!")
                        break
                except Exception:
                    pass
    elif is_logged_in:
        print("    [OK] Sesi login Facebook aktif ditemukan!")

    # Inisialisasi worker tab persisten untuk deep fetch
    _ensure_worker_tab()

    return FB_DRIVER


def _check_facebook_blocked(driver):
    """
    Mendeteksi apakah halaman Facebook menampilkan pesan Temporarily Blocked / Rate Limit,
    baik di modal dialog pop-up maupun di seluruh teks halaman.
    """
    if driver is None:
        return False
    try:
        check_js = """
        let texts = [];
        // 1. Cek dialog modal pop-up
        let dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"], div[aria-modal="true"]');
        dialogs.forEach(d => { if (d.innerText) texts.push(d.innerText.toLowerCase()); });
        
        // 2. Cek seluruh innerText dokumen
        if (document.body && document.body.innerText) {
            texts.push(document.body.innerText.toLowerCase());
        }
        
        let full = texts.join(' ');
        
        let blockPhrases = [
            'temporarily blocked',
            'misusing this feature',
            'going too fast',
            'you’ve been temporarily blocked',
            "you've been temporarily blocked",
            'you’re temporarily blocked',
            "you're temporarily blocked",
            'diblokir sementara',
            'menyalahgunakan fitur',
            'terlalu cepat',
            'kami membatasi',
            'tindakan ini diblokir',
            'coba lagi nanti',
            'try again later'
        ];
        
        return blockPhrases.some(phrase => full.includes(phrase));
        """
        return bool(driver.execute_script(check_js))
    except Exception:
        return False


def _dismiss_facebook_popups(driver):
    """
    Menutup dialog popup Facebook (termasuk popup 'Temporarily Blocked' / 'OK'):
    1. Klik tombol OK / Tutup / Close / Silang
    2. Hapus dialog overlay dari DOM jika tetap menghalangi tampilan dan scroll
    """
    if driver is None:
        return
    try:
        dismiss_js = """
        // 1. Klik tombol OK / Tutup / Close di dalam modal dialog
        let btns = document.querySelectorAll(
            'div[role="dialog"] div[role="button"], ' +
            'div[role="dialog"] button, ' +
            'div[role="alertdialog"] div[role="button"], ' +
            'div[role="alertdialog"] button, ' +
            'div[aria-modal="true"] div[role="button"], ' +
            'div[aria-modal="true"] button'
        );
        btns.forEach(btn => {
            let t = (btn.innerText || '').trim().toLowerCase();
            let aria = (btn.getAttribute('aria-label') || '').trim().toLowerCase();
            if (t === 'ok' || t === 'tutup' || t === 'close' || 
                aria === 'ok' || aria.includes('tutup') || aria.includes('close') || aria === 'oke') {
                try { btn.click(); } catch(e) {}
            }
        });

        // 2. Hapus overlay dialog popup 'Temporarily Blocked' agar tidak menghalangi tampilan dan scroll
        let dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"], div[aria-modal="true"]');
        dialogs.forEach(d => {
            let txt = (d.innerText || '').toLowerCase();
            if (txt.includes('temporarily blocked') || 
                txt.includes('diblokir sementara') || 
                txt.includes('misusing this feature') || 
                txt.includes('terlalu cepat') ||
                txt.includes('going too fast')) {
                try { d.remove(); } catch(e) {}
            }
        });

        // 3. Hapus juga backdrop/overlay gelap di belakang dialog jika ada
        let backdrops = document.querySelectorAll('div[data-pagelet*="Modal"], div.x1n2onr6[style*="position: fixed"]');
        backdrops.forEach(b => {
            let txt = (b.innerText || '').toLowerCase();
            if (txt.includes('temporarily blocked') || txt.includes('diblokir') || txt.includes('misusing this feature')) {
                try { b.remove(); } catch(e) {}
            }
        });
        """
        driver.execute_script(dismiss_js)
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
    except Exception:
        pass


def _force_relogin():
    """Tutup Chrome, bersihkan session/cookies lama, buka ulang & minta login akun Facebook baru."""
    global FB_DRIVER, FB_SEARCH_TAB, FB_WORKER_TAB

    print("\n" + "=" * 60)
    print("🚨 DETEKSI RATE LIMIT / TEMPORARILY BLOCKED FACEBOOK 🚨")
    print("Akun saat ini sedang terkena batas fitur sementara dari Facebook.")
    print("Mereset sesi browser agar Anda dapat login dengan akun Facebook baru/cadangan...")
    print("=" * 60)

    # 1. Tutup driver lama jika masih terbuka
    if FB_DRIVER is not None:
        try:
            FB_DRIVER.quit()
        except Exception:
            pass
        FB_DRIVER = None
        FB_SEARCH_TAB = None
        FB_WORKER_TAB = None

    time.sleep(2)

    # 2. Hapus profile Chrome lama agar session akun yang terblokir bersih total
    if os.path.exists(FB_PROFILE_DIR):
        try:
            shutil.rmtree(FB_PROFILE_DIR, ignore_errors=True)
            print("    [OK] Session & cookies akun lama berhasil dibersihkan.")
        except Exception as e:
            print(f"    [WARN] Gagal membersihkan folder profile: {e}")

    # 3. Buka Chrome baru dan pandu user login ke akun baru
    print("    [INFO] Membuka jendela Chrome baru untuk login akun baru...")
    _init_driver(skip_input=False)
    print("    [OK] Login akun baru berhasil! Melanjutkan proses scraping...\n")


def _ensure_worker_tab():
    """Memastikan ada 2 tab di Chrome: Tab 0 (Search Feed) dan Tab 1 (Worker Tab)."""
    global FB_DRIVER, FB_SEARCH_TAB, FB_WORKER_TAB
    if FB_DRIVER is None:
        return
    try:
        handles = FB_DRIVER.window_handles
        if len(handles) == 1:
            FB_SEARCH_TAB = handles[0]
            FB_DRIVER.switch_to.new_window('tab')
            FB_WORKER_TAB = FB_DRIVER.window_handles[-1]
            FB_DRIVER.switch_to.window(FB_SEARCH_TAB)
        elif len(handles) >= 2:
            FB_SEARCH_TAB = handles[0]
            FB_WORKER_TAB = handles[1]
    except Exception as e:
        print(f"    [WARN] Gagal inisialisasi worker tab: {e}")


def _deep_fetch_details(post_url):
    """
    Membuka post URL di worker tab untuk mengambil teks lengkap (unabridged)
    serta angka engagement asli tanpa merusak posisi scroll dan DOM pada search feed tab.
    """
    global FB_DRIVER, FB_WORKER_TAB
    if not post_url or not post_url.startswith('http') or 'facebook.com' not in post_url:
        return {}
    try:
        _ensure_worker_tab()
        if not FB_WORKER_TAB:
            return {}

        # Pindah ke worker tab
        FB_DRIVER.switch_to.window(FB_WORKER_TAB)
        while True:
            FB_DRIVER.get(post_url)
            time.sleep(random.uniform(2.0, 3.0))
            _dismiss_facebook_popups(FB_DRIVER)

            curr_url = (FB_DRIVER.current_url or '').lower()
            body_text = (FB_DRIVER.execute_script("return document.body.innerText") or "").lower()
            is_blocked = (
                any(x in curr_url for x in ['checkpoint', '/login', 'login.php']) or
                "temporarily blocked" in body_text or
                "diblokir sementara" in body_text or
                "masuk untuk melanjutkan" in body_text or
                "log in to continue" in body_text
            )
            if is_blocked:
                print("\n" + "=" * 60)
                print("🚨 FACEBOOK TERDETEKSI BOT / CHECKPOINT SAAT MEMUAT POST 🚨")
                print(f"URL yang gagal dimuat: {post_url}")
                print("1. Silakan selesaikan Login / Captcha / Konfirmasi di browser Chrome.")
                print("2. Pastikan Facebook sudah terbuka normal kembali.")
                print("=" * 60 + "\n")
                input("👉 TEKAN ENTER SETELAH LOGIN BERHASIL UNTUK RETRY MEMUAT URL INI... ")
                continue
            break

        # Buka tombol 'See more' / 'Selengkapnya' di viewer post
        expand_viewer_js = """
        document.querySelectorAll('div[role="button"], span[role="button"], span, div').forEach(el => {
            if (el.tagName === 'A' || el.closest('a')) return;
            let t = (el.innerText || '').trim().toLowerCase();
            let isSeeMore = /^(?:…|\\.\\.\\.)?\\s*(see more|lihat selengkapnya|selengkapnya|see original|lihat teks asli|lihat yang asli)\\s*(?:\\.\\.\\.|…)?$/i.test(t) ||
                            t.endsWith('see more') || t.endsWith('selengkapnya') || t.endsWith('lihat selengkapnya');
            if (isSeeMore) {
                try {
                    ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(evt => {
                        el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                    });
                    el.click();
                } catch(e) {}
            }
        });
        """
        try:
            FB_DRIVER.execute_script(expand_viewer_js)
            time.sleep(0.6)
        except:
            pass

        # Ekstrak caption terpanjang, tanggal upload, dan engagement dari post/photo viewer
        extract_details_js = """
        let res = { caption: '', likes: 0, comments: 0, shares: 0, date_raw: '' };

        let candidates = [];

        // 1. Ambil dari Schema.org JSON-LD (Jika tersedia dari server Meta)
        try {
            document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                try {
                    let j = JSON.parse(s.innerText || '{}');
                    let body = j.articleBody || j.caption || j.description || j.text;
                    if (body && typeof body === 'string' && body.trim().length > 15) {
                        candidates.push(body.trim());
                    }
                    if (j.datePublished || j.dateCreated) {
                        res.date_raw = j.datePublished || j.dateCreated;
                    }
                } catch(e) {}
            });
        } catch(e) {}

        // 2. Ambil dari OpenGraph meta tag
        try {
            let og = document.querySelector('meta[property="og:description"], meta[name="description"]');
            if (og) {
                let d = (og.getAttribute('content') || '').trim();
                if (d.length > 20 && !d.toLowerCase().startsWith('log in') && !d.toLowerCase().startsWith('masuk')) {
                    candidates.push(d);
                }
            }
        } catch(e) {}

        // 3. Ambil semua elemen teks berpotensi caption dari DOM
        let divs = Array.from(document.querySelectorAll('div[dir="auto"], span[dir="auto"]'))
            .filter(d => !d.closest('a') && !d.closest('h2, h3, h4') && !d.closest('div[role="toolbar"]') && !d.closest('form'))
            .map(d => (d.innerText || '').trim())
            .filter(t => t.length > 15 && 
                         !t.includes('\\u034f') &&
                         !/^(Komentar|Bagikan|Suka|Like|Comment|Share|Kirim|Send|Write a comment|Tulis komentar|Lihat komentar|Balas)/i.test(t) &&
                         !(/^(?:AI content|Sponsored|Bersponsor)/i.test(t) && t.length < 50) &&
                         !t.startsWith('http'));

        candidates = candidates.concat(divs);

        // Filter dan bersihkan teks kandidat
        let cleanCandidate = function(t) {
            return t.replace(/\\s*(?:…|\\.\\.\\.)?\\s*(?:see more|lihat selengkapnya|selengkapnya|see original|lihat teks asli)\\s*$/i, '').trim();
        };

        candidates = candidates.map(cleanCandidate).filter(t => t.length > 10);
        candidates.sort((a, b) => b.length - a.length);

        if (candidates.length > 0) {
            res.caption = candidates[0];
        }

        // 4. Ambil Tanggal Upload dari DOM (time[datetime] atau abbr[data-utime])
        if (!res.date_raw) {
            let timeEl = document.querySelector('abbr[data-utime], time[datetime], span[id*="time"] abbr');
            if (timeEl) {
                res.date_raw = timeEl.getAttribute('data-utime') || timeEl.getAttribute('datetime') || timeEl.innerText;
            }
        }

        // 5. Ambil Engagement dari aria-label
        let allEls = document.querySelectorAll('*[aria-label]');
        for (let el of allEls) {
            let label = el.getAttribute('aria-label').toLowerCase();
            let numMatch = label.match(/([\\.\\d,]+\\s*(?:k|m|rb|ribu|jt|juta)?)/i);
            if (!numMatch) continue;
            let numStr = numMatch[1];
            if (/(suka|like|reaksi|reaction)/i.test(label) && res.likes === 0) {
                res.likes = numStr;
            } else if (/(komentar|comment)/i.test(label) && res.comments === 0) {
                res.comments = numStr;
            } else if (/(bagikan|share)/i.test(label) && res.shares === 0) {
                res.shares = numStr;
            }
        }

        return res;
        """
        details = FB_DRIVER.execute_script(extract_details_js) or {}

        # CROSSCHECK VERIFIKASI: Cek apakah caption hasil deep fetch masih terpotong (...)
        caption = details.get('caption', '')
        if caption and (caption.endswith('…') or caption.endswith('...') or '...' in caption[-25:] or '…' in caption[-25:]):
            try:
                # Scroll post viewer dan coba klik ulang tombol 'See more'
                FB_DRIVER.execute_script("window.scrollBy(0, 350);")
                time.sleep(0.3)
                more_btns = FB_DRIVER.find_elements(By.XPATH, "//*[text()='See more' or text()='Lihat selengkapnya' or text()='Selengkapnya' or text()='See original' or text()='Lihat teks asli' or contains(text(), '... See more') or contains(text(), '... Lihat selengkapnya')]")
                for mb in more_btns:
                    try:
                        if mb.is_displayed():
                            ActionChains(FB_DRIVER).move_to_element(mb).click().perform()
                            time.sleep(0.2)
                    except:
                        pass
                # Re-extract
                re_details = FB_DRIVER.execute_script(extract_details_js) or {}
                if re_details.get('caption') and len(re_details['caption']) > len(caption):
                    details['caption'] = re_details['caption']
            except:
                pass

        # Ekstrak tanggal terformat
        raw_date = details.get('date_raw', '')
        if raw_date:
            d_str = str(raw_date).strip()
            if d_str.isdigit() and len(d_str) in [10, 13]:
                try:
                    val = int(d_str) if len(d_str) == 10 else int(d_str) // 1000
                    if 1577836800 <= val <= 1893456000:
                        details['created_at'] = datetime.fromtimestamp(val, tz=WIB).strftime('%Y-%m-%d %H:%M:%S WIB')
                except Exception:
                    pass
            elif 't' in d_str.lower() or re.match(r'^\d{4}-\d{2}-\d{2}', d_str):
                try:
                    iso_clean = d_str.replace('Z', '+00:00').replace('z', '+00:00')
                    dt = datetime.fromisoformat(iso_clean)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=WIB)
                    else:
                        dt = dt.astimezone(WIB)
                    details['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S WIB')
                except Exception:
                    pass

        return details
    except Exception as e:
        return {}


def _deep_fetch_caption(post_url):
    """Fallback kompatibilitas"""
    d = _deep_fetch_details(post_url)
    return d.get('caption', '')


def scrape_facebook(keyword, max_results=100):
    """
    Scrape postingan Facebook berdasarkan keyword dengan dynamic scrolling
    dan Deep-Fetch caption lengkap agar data tidak terpotong (tanpa tanda ...).
    
    Args:
        keyword: kata kunci pencarian
        max_results: target jumlah postingan
    """
    global FB_DRIVER, FB_SEARCH_TAB, FB_WORKER_TAB, _SEEN_URLS

    print(f"    - Facebook Selenium: mencari '{keyword}' (target: {max_results} data)...")

    if FB_DRIVER is None:
        print("    [!] Membuka Chrome untuk Facebook pertama kali...")
        _init_driver()

    _ensure_worker_tab()
    if FB_SEARCH_TAB:
        try:
            FB_DRIVER.switch_to.window(FB_SEARCH_TAB)
        except:
            pass

    query = urllib.parse.quote(keyword)
    url = f"https://www.facebook.com/search/posts/?q={query}"

    while True:
        try:
            FB_DRIVER.get(url)
            time.sleep(5)
            _dismiss_facebook_popups(FB_DRIVER)

            curr_url = (FB_DRIVER.current_url or '').lower()
            body_text = (FB_DRIVER.execute_script("return document.body.innerText") or "").lower()
            is_blocked = (
                any(x in curr_url for x in ['checkpoint', '/login', 'login.php']) or
                "temporarily blocked" in body_text or
                "diblokir sementara" in body_text or
                "masuk untuk melanjutkan" in body_text or
                "log in to continue" in body_text or
                "sesi anda telah berakhir" in body_text or
                "we noticed unusual activity" in body_text
            )
            if is_blocked:
                print("\n" + "=" * 60)
                print("🚨 FACEBOOK TERDETEKSI BOT / CHECKPOINT PADA SEARCH URL 🚨")
                print(f"Keyword in-progress: '{keyword}'")
                print(f"URL pencarian: {url}")
                print("1. Silakan selesaikan Login / Captcha / Konfirmasi di browser Chrome.")
                print("2. Pastikan Facebook sudah terbuka normal dan beranda bisa diakses.")
                print("=" * 60 + "\n")
                input("👉 TEKAN ENTER SETELAH LOGIN BERHASIL UNTUK MELANJUTKAN SEARCH INI... ")
                continue
            break
        except Exception as e:
            print(f"    [ERROR] Gagal membuka URL search: {e}")
            break

    # ============================================================
    # FASE 1: KUMPULKAN POSTINGAN DARI FEED PENCARIAN (SCROLLING)
    # ============================================================
    print(f"    [INFO] Fase 1: Mengumpulkan postingan dari feed pencarian '{keyword}'...")
    collected_posts = {}  # Dict: url_post -> post_data
    seen_in_kw = set()
    no_new_count = 0
    max_no_new = 12

    while len(collected_posts) < max_results:
        count_before = len(collected_posts)

        # 1. URL GUARDIAN: Pastikan browser tidak tersesat ke halaman grup/komunitas
        try:
            curr_url = FB_DRIVER.current_url
            if "/search/posts" not in curr_url:
                print(f"      [GUARDIAN] Browser teralihkan ke luar pencarian ({curr_url[:65]}...). Mengembalikan...")
                FB_DRIVER.get(url)
                time.sleep(4)
                continue
        except Exception:
            pass

        # 2. POPUP / MODAL DISMISSER & BOT DETECTION:
        _dismiss_facebook_popups(FB_DRIVER)
        curr_url_check = (FB_DRIVER.current_url or '').lower()
        body_text_check = (FB_DRIVER.execute_script("return document.body.innerText") or "").lower()
        if (any(x in curr_url_check for x in ['checkpoint', '/login', 'login.php']) or
            "temporarily blocked" in body_text_check or "diblokir sementara" in body_text_check):
            print("\n" + "=" * 60)
            print("🚨 FACEBOOK TERDETEKSI BOT / LIMIT DI TENGAH SCROLL 🚨")
            print(f"Keyword in-progress: '{keyword}' ({len(collected_posts)} data terkumpul)")
            print("1. Silakan selesaikan Login / Captcha / Konfirmasi di browser Chrome.")
            print("2. Pastikan beranda/pencarian sudah normal kembali.")
            print("=" * 60 + "\n")
            input("👉 TEKAN ENTER SETELAH LOGIN BERHASIL UNTUK MELANJUTKAN SEARCH INI... ")
            FB_DRIVER.get(url)
            time.sleep(5)
            continue

        # 3. EXPAND POST TEXT AMAN PADA FEED: Klik 'See more' / 'Lihat selengkapnya' dengan ActionChains & JS
        try:
            # A. Selenium ActionChains click pada tombol yang terlihat di viewport
            see_mores = FB_DRIVER.find_elements(By.XPATH, "//*[text()='See more' or text()='Lihat selengkapnya' or text()='Selengkapnya']")
            for sm in see_mores:
                try:
                    if sm.is_displayed():
                        FB_DRIVER.execute_script("arguments[0].scrollIntoView({block: 'center'});", sm)
                        time.sleep(0.08)
                        ActionChains(FB_DRIVER).move_to_element(sm).click().perform()
                        time.sleep(0.12)
                except Exception:
                    pass
        except Exception:
            pass

        # B. Fallback JavaScript dispatch click untuk semua container feed
        expand_js = """
        let feed = document.querySelector('div[role="feed"]') || document.body;
        let candidates = feed.querySelectorAll('div[role="button"], span[role="button"], span, div');
        candidates.forEach(el => {
            if (el.tagName === 'A' || el.closest('a')) return;
            let txt = (el.innerText || '').trim().toLowerCase();
            if (txt.includes('grup') || txt.includes('group') || txt.includes('komunitas') || 
                txt.includes('tentang') || txt.includes('about') || txt.includes('aturan') || 
                txt.includes('rules') || txt.includes('anggota') || txt.includes('members')) {
                return;
            }
            let isSeeMore = /^(?:…|\\.\\.\\.)?\\s*(see more|lihat selengkapnya|selengkapnya)\\s*$/i.test(txt) ||
                            txt === 'see more' || txt === 'lihat selengkapnya';
            if (isSeeMore) {
                try {
                    ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(evt => {
                        el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                    });
                    el.click();
                } catch(e) {}
            }
        });
        """
        try:
            FB_DRIVER.execute_script(expand_js)
            time.sleep(0.4)
        except:
            pass

        # 4. Ekstrak data via JavaScript dari DOM feed
        raw_posts = _extract_via_js(FB_DRIVER)

        for post in raw_posts:
            if len(collected_posts) >= max_results:
                break

            url_post = post.get('url', '')
            if not url_post or url_post in _SEEN_URLS or url_post in seen_in_kw:
                continue

            seen_in_kw.add(url_post)

            author = post.get('author', '')
            author = author.replace('\u034f', '')
            author = re.sub(r'(?i)online status indicator|active|aktif', '', author)
            author = re.sub(r'[\r\n\t]+', ' ', author).strip()
            author = re.sub(r'·\s*Join|·\s*Follow|·', '', author, flags=re.IGNORECASE).strip()
            author = re.split(r'(?i)(is at |is in |sedang di )', author)[0].strip()
            author = author[:50]
            if not author or len(author) < 2 or re.search(r'^(?:see more|lihat selengkapnya)$', author, re.IGNORECASE):
                author = "Facebook_User"

            content = _clean_text(post.get('content', ''))
            if len(content) < 15:
                continue

            likes = _clean_engagement(post.get('likes', '0'))
            comments = _clean_engagement(post.get('comments', '0'))
            shares = _clean_engagement(post.get('shares', '0'))

            u_clean = url_post.lower()
            post_type = "Reel" if "/reel/" in u_clean else ("Video" if "/videos/" in u_clean or "/watch/" in u_clean else ("Photo" if "/photo/" in u_clean else "Post"))
            handle = f"@{re.sub(r'[^\w\.-]', '_', author).lower()}" if author else "@facebook_user"
            post_id = f"fb_{abs(hash(url_post)) % 1000000:06d}"

            collected_posts[url_post] = {
                "post_id": post_id,
                "platform": "Facebook",
                "post_type": post_type,
                "author": author,
                "handle": handle,
                "content": content,
                "created_at": datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB'),
                "likes": int(likes) if str(likes).isdigit() else 0,
                "comments": int(comments) if str(comments).isdigit() else 0,
                "shares": int(shares) if str(shares).isdigit() else 0,
                "url": url_post,
                "keyword": keyword,
                "scraped_at": datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB'),
                "topic": "UNKNOWN",
                "description": ""
            }

        new_count = len(collected_posts) - count_before
        if new_count > 0:
            print(f"      [Scroll] {len(collected_posts)}/{max_results} Data terkumpul (+{new_count} baru)")
            no_new_count = 0
        else:
            no_new_count += 1
            if no_new_count >= max_no_new:
                print(f"    [INFO] Mentok! {max_no_new}x scroll tanpa postingan baru.")
                break

        if len(collected_posts) >= max_results:
            break

        # 5. Scroll ke bawah (tetap di search tab!)
        if no_new_count >= 2:
            FB_DRIVER.execute_script("window.scrollBy(0, -400);")
            time.sleep(0.3)
            FB_DRIVER.execute_script("window.scrollBy(0, 1400); window.scrollTo(0, document.body.scrollHeight);")
            try:
                body_el = FB_DRIVER.find_element(By.TAG_NAME, 'body')
                body_el.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)
                body_el.send_keys(Keys.PAGE_DOWN)
            except:
                pass
        else:
            FB_DRIVER.execute_script("window.scrollBy(0, 1000); window.scrollTo(0, document.body.scrollHeight);")
            try:
                FB_DRIVER.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            except:
                pass

        time.sleep(random.uniform(1.8, 2.8))

    print(f"\n    [INFO] Fase 1 Selesai: Total {len(collected_posts)} postingan berhasil dikumpulkan.")

    # ============================================================
    # FASE 2: BUKA SATU PER SATU UNTUK DETAIL LENGKAP (DEEP-FETCH)
    # ============================================================
    # Lakukan Deep-Fetch untuk SEMUA postingan yang teksnya masih terindikasi terpotong (...)
    valid_prefix_check = lambda u: any(x in u for x in ['/posts/', '/permalink/', 'fbid=', '/photo/', '/videos/', '/watch/', 'story_fbid=', '/reel/'])
    
    def _is_truncated_fb(content):
        if not content:
            return True
        c = content.strip()
        if c.endswith('…') or c.endswith('...'):
            return True
        if '...' in c[-30:] or '…' in c[-30:]:
            return True
        if re.search(r'\b(see more|lihat selengkapnya|selengkapnya)\b', c, re.IGNORECASE):
            return True
        if len(c) < 80:
            return True
        return False

    posts_to_fetch = [
        (u, d) for u, d in collected_posts.items()
        if valid_prefix_check(u) and _is_truncated_fb(d['content'])
    ]

    if posts_to_fetch:
        print(f"    [INFO] Fase 2: Membuka SEMUA {len(posts_to_fetch)} postingan yang terindikasi terpotong di Worker Tab untuk mengambil teks utuh...")
        _ensure_worker_tab()

        for idx, (url_post, data) in enumerate(posts_to_fetch, 1):
            c_preview = data['content'][:45].replace('\n', ' ')
            print(f"      [{idx}/{len(posts_to_fetch)}] Deep-Fetch: {url_post[:60]}... ({len(data['content'])} char: '{c_preview}...')")
            
            details = _deep_fetch_details(url_post)
            if details:
                # 1. Update Teks jika versi detail lebih panjang & lengkap
                if details.get('caption'):
                    new_caption = _clean_text(details['caption'])
                    if len(new_caption) > len(data['content']):
                        print(f"        [OK] Teks diperluas: {len(data['content'])} -> {len(new_caption)} karakter!")
                        data['content'] = new_caption

                # 2. Update Engagement jika versi detail menemukan angka yang lebih valid
                if details.get('likes'):
                    l = _clean_engagement(details['likes'])
                    if str(l).isdigit() and int(l) > data['likes']:
                        data['likes'] = int(l)

                if details.get('comments'):
                    c = _clean_engagement(details['comments'])
                    if str(c).isdigit() and int(c) > data['comments']:
                        data['comments'] = int(c)

                if details.get('shares'):
                    s = _clean_engagement(details['shares'])
                    if str(s).isdigit() and int(s) > data['shares']:
                        data['shares'] = int(s)

                if details.get('created_at'):
                    data['created_at'] = details['created_at']

            time.sleep(random.uniform(1.0, 1.8))

        # Kembalikan fokus ke Search Tab setelah selesai
        if FB_SEARCH_TAB:
            try:
                FB_DRIVER.switch_to.window(FB_SEARCH_TAB)
            except:
                pass

    # ============================================================
    # DEDUPLIKASI AKHIR & PEMBENTUKAN HASIL
    # ============================================================
    results = []
    seen_content_keys = set()

    for url_post, data in collected_posts.items():
        # Masukkan ke set URL global agar tidak diulang di keyword lain
        _SEEN_URLS.add(url_post)

        raw_c = str(data.get('content', '')).strip()

        # 1. Pastikan caption tidak kosong dan bukan pesan error
        if not raw_c or len(raw_c) < 15:
            continue

        # 2. Cek apakah caption masih terpotong (...)
        if raw_c.endswith('...') or raw_c.endswith('…'):
            print(f"      [WARN] Postingan FB {url_post[:45]}... masih terpotong (...). Skip agar tidak menyimpan teks buntung.")
            continue

        # 3. REGULASI FILTER TOPIK (Kementerian_PU / Menteri_PU)
        matched_topic = detect_topic(raw_c) if detect_topic else None
        if not matched_topic:
            c_snip = raw_c[:45].replace('\n', ' ')
            print(f"      [FILTER REJECT] Postingan FB diabaikan karena bukan topik penelitian (Off-topic): '{c_snip}...'")
            continue

        data['topic'] = matched_topic

        # Format penyimpanan standar CSV identik dengan Instagram
        formatted_c = re.sub(r'[\u200e\u200f]\s*[\u200e\u200f]', ' |  | ', raw_c)
        formatted_c = formatted_c.replace('\r', '').replace('\n\n', ' |  | ').replace('\n', ' | ')
        formatted_c = re.sub(r'(\s*\|\s*){2,}', ' |  | ', formatted_c)
        formatted_c = re.sub(r'[\u200e\u200f\ufffd]', '', formatted_c).strip(' |')
        data['content'] = formatted_c

        # User Rule: URL adalah Primary Key. Jangan hapus jika konten mirip, hanya hapus jika URL sama.
        results.append(data)
        print(f"        ✨ [PASSED REGULASI FB] Topik: {matched_topic} | {len(raw_c)} char | Likes: {data.get('likes', 0)}")

    # Cek jika 0 postingan didapat karena limit / captcha / logout
    if len(results) == 0:
        try:
            curr_url = FB_DRIVER.current_url.lower()
            is_limited = (_check_facebook_blocked(FB_DRIVER) or 
                          "checkpoint" in curr_url or 
                          "login" in curr_url)
            if is_limited:
                print("\n" + "=" * 60)
                print("🚨 FACEBOOK MEMBATASI PENCARIAN / PERLU LOGIN AKUN BARU 🚨")
                print(f"Keyword '{keyword}' menghasilkan 0 post (terindikasi limit / temporarily blocked).")
                print("=" * 60 + "\n")
                _force_relogin()
                return scrape_facebook(keyword, max_results=max_results)
        except RecursionError:
            pass
        except Exception:
            pass

    print(f"    [OK] Selesai. Total {len(results)} data Facebook berhasil diekstrak.")
    return results


# ============================================================
# TEST
def enrich_single_facebook_post(url_post):
    """
    Membuka 1 URL postingan Facebook secara langsung dan mengambil 100% caption utuh
    dengan auto-expand 'See more' / 'Lihat selengkapnya' serta crosscheck verification.
    """
    global FB_DRIVER
    if not url_post or 'facebook.com' not in url_post:
        return {}

    if FB_DRIVER is None:
        _init_driver()

    details = _deep_fetch_details(url_post)
    if details.get('caption'):
        details['caption'] = _clean_text(details['caption'])
    return details


# ============================================================
if __name__ == "__main__":
    print("[TEST] Memulai test scrape Facebook (Selenium)...")
    data = scrape_facebook("Kementerian Pekerjaan Umum", max_results=10)
    print(f"Berhasil ambil {len(data)} data")
    if FB_DRIVER:
        FB_DRIVER.quit()
