from pathlib import Path
import requests

reel_id = 'Db_aVwFEkfD'
urls = [
    f'https://www.instagram.com/reel/{reel_id}/?__a=1&__d=dis',
    f'https://www.instagram.com/p/{reel_id}/?__a=1&__d=dis',
    f'https://www.instagram.com/reel/{reel_id}/',
]
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36',
    'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}
root = Path('/home/ubuntu/furia-clips-rebuild/docs/instagram-reel-probes')
root.mkdir(parents=True, exist_ok=True)
for index, url in enumerate(urls, 1):
    response = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
    out = root / f'probe-{index}.txt'
    out.write_text(f'URL {url}\nSTATUS {response.status_code}\nFINAL {response.url}\nCONTENT_TYPE {response.headers.get("content-type")}\n\n{response.text}', encoding='utf-8')
    print(index, response.status_code, response.url, response.headers.get('content-type'), len(response.text))
