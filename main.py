import sys
import json
import time
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from fake_useragent import UserAgent

def run_bot(proxy_url):
    # Membaca konfigurasi dari file JSON
    with open('config.json', 'r') as f:
        config = json.load(f)

    ua = UserAgent(platforms=[config['platform']])
    
    with sync_playwright() as p:
        print(f"[*] Menjalankan Chrome dengan proxy: {proxy_url}")
        try:
            browser = p.chromium.launch(
                headless=True, # Ubah ke False jika Anda ingin melihat browser terbuka di PC lokal
                proxy={"server": proxy_url},
                args=['--disable-blink-features=AutomationControlled']
            )
            
            viewport = {'width': 1366, 'height': 768} if config['platform'] == 'desktop' else {'width': 390, 'height': 844}
            
            context = browser.new_context(
                user_agent=ua.random,
                locale=config['language'],
                viewport=viewport
            )
            
            page = context.new_page()
            stealth_sync(page)

            # 1. Buka Search Engine
            page.goto(f"https://{config['search_engine']}", timeout=60000)
            
            # 2. Cari Keyword
            search_box = page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=15000)
            
            # Memilih satu keyword secara acak jika bentuknya adalah list (banyak keyword)
            if isinstance(config['keyword'], list):
                target_keyword = random.choice(config['keyword'])
            else:
                target_keyword = config['keyword']
                
            print(f"[*] Proxy {proxy_url} menggunakan keyword: {target_keyword}")
            
            search_box.fill(target_keyword)
            search_box.press("Enter")
            page.wait_for_load_state("networkidle")

            # 3. Logika CTR: Scroll dan Cari URL Target
            found = False
            for _ in range(3): # Maksimal scroll 3x ke bawah
                links = page.locator(f"a[href*='{config['target_domain']}']").all()
                if links:
                    random.choice(links).click()
                    found = True
                    break
                page.mouse.wheel(0, 800)
                time.sleep(2)

            if found:
                print(f"[+] Berhasil masuk ke {config['target_domain']} via {proxy_url}")
                
                # 4. Delay acak di Main Web & Scroll
                delay = random.randint(config['min_delay_main'], config['max_delay_main'])
                time.sleep(delay / 2)
                page.mouse.wheel(0, random.randint(300, 700))
                time.sleep(delay / 2)

                # 5. Anti-Bounce: Klik link internal
                internal_links = page.locator(f"a[href^='/'], a[href*='{config['target_domain']}']").all()
                if len(internal_links) > 1:
                    sub_page = random.choice(internal_links[1:min(5, len(internal_links))])
                    sub_page.click()
                    print(f"[*] Menjelajahi sub-page untuk proxy {proxy_url}...")
                    time.sleep(config['subpage_duration'])
                    print(f"[+] Selesai. Bounce rate dicegah.")
                else:
                    print(f"[-] Tidak ada link internal ditemukan.")
            else:
                print(f"[-] Target {config['target_domain']} tidak ada di halaman pencarian (Proxy: {proxy_url}).")

        except Exception as e:
            print(f"[!] Gagal pada proxy {proxy_url}: Konek timeout atau IP diblokir.")
        finally:
            if 'browser' in locals():
                browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_bot(sys.argv[1])
