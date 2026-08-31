import os
import tempfile
from modules.video_cutter import VideoCutter

# Use the test fixture as source
fixture = "/c/Users/70156213125/furia-clips/tests/fixtures/sample_av.mp4"
print(f"Fixture exists: {os.path.exists(fixture)}")

with tempfile.TemporaryDirectory() as tmpdir:
    output = os.path.join(tmpdir, "test_clip.mp4")
    cutter = VideoCutter(preset="shorts")
    result = cutter.cut_video(fixture, 0.0, 1.5, output)
    print(f"Cut result: {result}")
    print(f"Output exists: {os.path.exists(result)}")
    if os.path.exists(result):
        size = os.path.getsize(result)
        print(f"Output size: {size} bytes")
        
        # Verify with ffprobe
        import subprocess
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0", result
        ], capture_output=True, text=True)
        print(f"ffprobe: {probe.stdout.strip()}")