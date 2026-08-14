from pathlib import Path
import json
import re
import requests

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
OUT = ROOT / 'workspace' / 'audit_drive_clips'
OUT.mkdir(parents=True, exist_ok=True)
entries = json.loads((ROOT / 'docs' / 'drive-folder-files.json').read_text(encoding='utf-8'))
entries = [item for item in entries if re.match(r'^(?:[1-9]|1[0-5])\.\s', item['name'])]
s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 Furia-Clips-Audit'
for item in entries:
    file_id = item.get('file_id_candidate')
    if not file_id or file_id.startswith('x'):
        continue
    target = OUT / item['name']
    if target.exists() and target.stat().st_size > 0:
        print('SKIP', target.name)
        continue
    url = f'https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t'
    response = s.get(url, stream=True, timeout=60)
    content_type = response.headers.get('content-type', '')
    if response.status_code != 200 or 'text/html' in content_type:
        print('FAIL', item['name'], response.status_code, content_type)
        continue
    with target.open('wb') as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    print('OK', target.name, target.stat().st_size)
