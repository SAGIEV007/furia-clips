from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
INPUT = ROOT / 'workspace' / 'instagram_mbl_sample'
OUTPUT = ROOT / 'workspace' / 'instagram_mbl_contact_sheets'
OUTPUT.mkdir(parents=True, exist_ok=True)

for video in sorted(INPUT.glob('*.mp4')):
    out_dir = OUTPUT / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_pattern = out_dir / 'frame_%02d.jpg'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video),
        '-vf', "fps=1/8,scale=320:-2,tile=3x2",
        '-frames:v', '1', '-q:v', '5', '-y', str(out_dir / 'sheet.jpg'),
    ], check=False)
    print(video.stem, (out_dir / 'sheet.jpg').exists())
