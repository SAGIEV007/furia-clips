import os
import tempfile
import unittest

from modules.media_validation import validate_media
from modules.video_cutter import VideoCutter


FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")


@unittest.skipUnless(os.path.exists(FIXTURE), "fixture de mídia ainda não foi gerada")
class VideoCutterTests(unittest.TestCase):
    def test_cut_clip_renders_vertical_with_audio(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "vertical.mp4")
            cutter = VideoCutter(preset="shorts")
            result = cutter.cut_clip(FIXTURE, 0, 1.5, output, vertical=True)
            self.assertEqual(result, output)
            validation = validate_media(
                output,
                expected_width=1080,
                expected_height=1920,
                expected_duration=1.5,
                duration_tolerance=0.5,
                require_audio=True,
            )
            self.assertTrue(validation.valid, validation.as_dict())

    def test_debate_layout_preserves_full_frame_inside_vertical_canvas(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "debate.mp4")
            cutter = VideoCutter(preset="shorts")
            result = cutter.cut_clip(
                FIXTURE, 0, 1.0, output, vertical=True, video_layout="debate"
            )
            self.assertEqual(result, output)
            validation = validate_media(
                output,
                expected_width=1080,
                expected_height=1920,
                expected_duration=1.0,
                duration_tolerance=0.5,
                require_audio=True,
            )
            self.assertTrue(validation.valid, validation.as_dict())


if __name__ == "__main__":
    unittest.main()


def test_detect_scenes_handles_empty_stderr(monkeypatch):
    from types import SimpleNamespace
    import modules.video_cutter as module

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stderr=None, returncode=0),
    )
    assert VideoCutter().detect_scenes("video.mp4") == [0.0]
