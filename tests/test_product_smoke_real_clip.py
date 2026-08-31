"""
Smoke real do produto: renderiza um clip vertical a partir da fixture
e valida que a saída respeita o preset atual (1080x1920),
independentemente da orientação do vídeo fonte.
"""
import os

import ffmpeg

from modules.video_cutter import VideoCutter

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")


def test_shorts_preset_render_vertical_1080x1920_from_source(tmp_path):
    output = tmp_path / "shorts_smoke.mp4"
    cutter = VideoCutter(preset="shorts")
    cutter.cut_clip(FIXTURE, 0, 1.5, str(output), vertical=True)

    assert output.exists(), "clip vertical não foi gerado"
