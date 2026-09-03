import os
import sys
import tempfile
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.video_cutter import VideoCutter

REAL_VIDEO = os.path.join(ROOT, "FuriaClipsData", "downloads", "RENAN_SANTOS_-_Flow_News_065 [oGK5E24zTbI].mp4")
print(f"Real video exists: {os.path.exists(REAL_VIDEO)}")
if not os.path.exists(REAL_VIDEO):
    raise SystemExit(1)

with tempfile.TemporaryDirectory() as tmpdir:
    output = os.path.join(tmpdir, "flow065_smoke.mp4")
    cutter = VideoCutter(preset="shorts")
    result = cutter.cut_clip(REAL_VIDEO, 0.0, 1.5, output)
    print(f"Cut result: {result}")
    print(f"Output exists: {os.path.exists(result)}")
    if result and os.path.exists(result):
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration",
             "-of", "csv=p=0", result],
            capture_output=True, text=True
        )
        print(f"ffprobe: {probe.stdout.strip()}")
