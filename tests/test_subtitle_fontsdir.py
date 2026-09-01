import os
import tempfile
from unittest.mock import patch, MagicMock

from modules.subtitle_generator import SubtitleGenerator


def test_burn_subtitles_includes_fontsdir():
    with tempfile.TemporaryDirectory() as tmp:
        ass_path = os.path.join(tmp, "subs.ass")
        open(ass_path, "w", encoding="utf-8").close()
        fonts_dir = os.path.join(tmp, "fonts")
        os.makedirs(fonts_dir, exist_ok=True)
        open(os.path.join(fonts_dir, "Montserrat-Bold.ttf"), "wb").close()

        generator = SubtitleGenerator()
        fake_result = MagicMock()
        fake_result.returncode = 0
        with patch("modules.subtitle_generator.subprocess.run", return_value=fake_result) as mock_run:
            generator.burn_subtitles("dummy.mp4", ass_path, output_path=os.path.join(tmp, "out.mp4"))
            assert mock_run.called
            cmd = mock_run.call_args[0][0]
            ass_filter = next(arg for arg in cmd if arg.startswith("ass=fontsdir="))
            assert ass_filter.startswith("ass=fontsdir=")
            assert fonts_dir.replace("\\", "/") in ass_filter
