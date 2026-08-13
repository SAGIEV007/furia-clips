from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
CATALOG = ROOT / 'docs' / 'instagram-feed-catalog-full.json'

parser = argparse.ArgumentParser()
parser.add_argument('--profile', required=True)
parser.add_argument('--limit', type=int, default=12)
parser.add_argument('--offset', type=int, default=0)
parser.add_argument('--output', default='workspace/instagram_profile_sample')
args = parser.parse_args()

payload = json.loads(CATALOG.read_text(encoding='utf-8'))
profile = payload['profiles'][args.profile]
entries = [entry for entry in profile.get('entries', []) if entry.get('is_video')]
selected = entries[args.offset:args.offset + args.limit]
out_dir = ROOT / args.output
out_dir.mkdir(parents=True, exist_ok=True)

for index, entry in enumerate(selected, args.offset + 1):
    destination = out_dir / f"{entry['code']}.mp4"
    if destination.exists() and destination.stat().st_size > 0:
        print(index, 'exists', entry['code'], flush=True)
        continue
    command = [
        'yt-dlp', '--no-playlist', '--no-warnings', '--restrict-filenames',
        '-f', 'bv*[height<=1080]+ba/b[height<=1080]/b',
        '--merge-output-format', 'mp4',
        '-o', str(out_dir / f"{entry['code']}.%(ext)s"),
        entry['url'],
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    status = 'ok' if result.returncode == 0 else f'error:{result.returncode}'
    print(index, status, entry['code'], entry['url'], flush=True)
    if result.returncode != 0:
        print(result.stderr[-500:], flush=True)
