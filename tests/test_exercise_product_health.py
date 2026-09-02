import os
import tempfile
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.video_cutter import VideoCutter


def test_exercise_product_generates_valid_short_clip():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")
    fixture = os.path.normpath(fixture)
    assert os.path.exists(fixture), f"fixture sample_av.mp4 ausente em {fixture}"

    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "test_clip.mp4")
        cutter = VideoCutter(preset="shorts")
        result = cutter.cut_clip(fixture, 0.0, 1.5, output)

        assert result and os.path.exists(result), "exercise_product nao gerou clip"

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,duration",
                "-of",
                "csv=p=0",
                result,
            ],
            capture_output=True,
            text=True,
        )
        assert probe.returncode == 0, f"ffprobe falhou: {probe.stderr}"
        width, height, duration = probe.stdout.strip().split(",")
        assert int(width) == 1080
        assert int(height) == 1920
        assert float(duration) > 0
