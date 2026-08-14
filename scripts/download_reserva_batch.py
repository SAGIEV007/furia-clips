from pathlib import Path
import subprocess

root = Path('/home/ubuntu/furia-clips-rebuild')
url_file = root / 'docs' / 'instagram-reserva-visible-reels.txt'
out_dir = root / 'workspace' / 'instagram_reserva'
out_dir.mkdir(parents=True, exist_ok=True)
urls = [line.strip() for line in url_file.read_text(encoding='utf-8').splitlines() if line.strip()]
for index, url in enumerate(urls, 1):
    command = [
        'yt-dlp', '--no-playlist', '--no-warnings', '--restrict-filenames',
        '-o', str(out_dir / '%(id)s.%(ext)s'), url,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    status = 'ok' if result.returncode == 0 else f'error:{result.returncode}'
    print(index, status, url)
    if result.returncode != 0:
        print(result.stderr[-500:])
