from pathlib import Path
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "workspace" / "instagram_reserva"
OUT_DIR = ROOT / "workspace" / "instagram_reserva_contact_sheets"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ITEMS = {
    "Db_OfZDjKMW": 12,
    "Db_R92njTCq": 12,
    "Db_VUXqjnyO": 8,
    "Db_Y07LFV7J": 12,
    "Db_aVwFEkfD": 12,
}

def duration(video):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)], text=True)
    return float(out.strip())

for clip_id, count in ITEMS.items():
    video = VIDEO_DIR / f"{clip_id}.mp4"
    dur = duration(video)
    with __import__("tempfile").TemporaryDirectory(prefix=f"sheet_{clip_id}_") as tmp:
        tmp = Path(tmp)
        frames = []
        for i in range(count):
            ts = min(dur - min(1.0, max(0.5, dur * 0.02)), dur * i / max(1, count - 1))
            path = tmp / f"{i:02d}.jpg"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "3", "-y", str(path)], check=True)
            image = Image.open(path).convert("RGB")
            frames.append((ts, image))
        cell_w, cell_h = 380, 300
        cols = 4
        rows = math.ceil(len(frames) / cols)
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#202020")
        draw = ImageDraw.Draw(sheet)
        for i, (ts, image) in enumerate(frames):
            x = (i % cols) * cell_w + 10
            y = (i // cols) * cell_h + 28
            image.thumbnail((cell_w - 20, cell_h - 50))
            sheet.paste(image, (x + ((cell_w - 20) - image.width) // 2, y))
            draw.text((x, y - 22), f"{i:02d}  {ts:06.1f}s", fill="white")
        out = OUT_DIR / f"{clip_id}.jpg"
        sheet.save(out, quality=92)
        print(out)
