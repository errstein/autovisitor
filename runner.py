import json
import subprocess
import multiprocessing
import requests
from concurrent.futures import ThreadPoolExecutor

def fetch_proxies_from_api(api_url):
    """Mengambil daftar proxy terbaru dari API"""
    try:
        print(f"[*] Mengunduh proxy dari API ProxyScrape...")
        response = requests.get(api_url, timeout=15)
        response.raise_for_status() # Pastikan request sukses (Status 200)
        
        # API mereturn teks dengan format baris baru (\n)
        proxies = [line.strip() for line in response.text.split('\n') if line.strip()]
        return proxies
    except Exception as e:
        print(f"[-] Gagal mengambil proxy dari API: {e}")
        return []

def check_proxy(proxy):
    """Menyaring proxy gratisan yang sudah mati sebelum digunakan Playwright"""
    # ProxyScrape API v4 dengan format 'protocolipport' biasanya mereturn seperti 'http://ip:port'
    proxies_dict = {"http": proxy, "https": proxy}
    try:
        # Kita test koneksi ke Google dengan batas waktu 5 detik agar cepat
        res = requests.get("https://www.google.com", proxies=proxies_dict, timeout=5)
        if res.status_code == 200:
            return proxy
    except:
        pass # Jika gagal/timeout, abaikan saja
    return None

def start_worker(proxy):
    """Memanggil main.py sebagai sub-proses"""
    print(f"[>] Memulai browser dengan proxy: {proxy}")
    subprocess.run(["python", "main.py", proxy])

if __name__ == "__main__":
    # 1. Baca Konfigurasi Parameter
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("[-] File config.json tidak ditemukan! Pastikan file berada di folder yang sama.")
        exit()

    # 2. Ambil Proxy dari API
    proxy_api_url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
    raw_proxies = fetch_proxies_from_api(proxy_api_url)

    if not raw_proxies:
        print("[-] Tidak mendapatkan proxy dari API. Hentikan program.")
        exit()
        
    print(f"[+] Berhasil mendapatkan {len(raw_proxies)} proxy mentah. Mulai pengecekan (ini memakan waktu sebentar)...")

    # 3. Cek proxy secara paralel agar proses pengecekan ribuan IP berjalan sangat cepat
    working_proxies = []
    # Menggunakan 50 thread sekaligus untuk mengecek proxy
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_proxy, raw_proxies)
        for res in results:
            if res:
                working_proxies.append(res)
                # Jika sudah mendapatkan jumlah proxy aktif sebanyak target visitor, kita bisa hentikan pencarian agar hemat waktu
                if len(working_proxies) >= config['max_visitors']:
                    break

    print(f"\n[+] Ditemukan {len(working_proxies)} proxy yang responsif & aktif.")

    if not working_proxies:
        print("[-] Semua proxy dari API mati atau terlalu lambat. Coba jalankan ulang nanti.")
        exit()

    # 4. Jalankan bot secara paralel sesuai proxy yang hidup
    target_visitors = min(config['max_visitors'], len(working_proxies))
    print(f"[*] Menjalankan {target_visitors} instance Chrome secara simultan...\n")

    processes = []
    for i in range(target_visitors):
        p = multiprocessing.Process(target=start_worker, args=(working_proxies[i],))
        processes.append(p)
        p.start()

    # Tunggu semua browser selesai bekerja
    for p in processes:
        p.join()
        
    print("\n[+] Semua tugas automasi pengujian telah selesai.")
