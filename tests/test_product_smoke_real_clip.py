"""
Smoke real do produto: renderiza um clip vertical a partir da fixture
e valida que a saída respeita o preset atual (1080x1920) e a duração solicitada.
"""
import os

from modules.media_validation import validate_media
from modules.video_cutter import VideoCutter

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")


def test_shorts_preset_render_vertical_1080x1920_from_source(tmp_path):
    output = tmp_path / "shorts_smoke.mp4"
    cutter = VideoCutter(preset="shorts")
    cutter.cut_clip(FIXTURE, 0, 1.5, str(output), vertical=True)

    assert output.exists(), "clip vertical não foi gerado"

    validation = validate_media(
        str(output),
        expected_width=1080,
        expected_height=1920,
        expected_duration=1.5,
        duration_tolerance=0.5,
        require_audio=True,
    )
    assert validation.valid, validation.as_dict()
