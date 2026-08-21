import os
import tempfile
import unittest

from modules.subtitle_generator import SubtitleGenerator


class SubtitleGeneratorTests(unittest.TestCase):
    def test_generates_word_by_word_ass_with_safe_text(self):
        generator = SubtitleGenerator({"render_preset": "shorts", "subtitle_style": "word_by_word"})
        segments = [
            {
                "start": -0.5,
                "end": 1.2,
                "text": "Atenção {agora}",
                "words": [
                    {"word": "Atenção", "start": -0.5, "end": 0.4},
                    {"word": "{agora}", "start": 0.4, "end": 1.2},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "captions.ass")
            generator.generate_ass_file(segments, path)
            with open(path, encoding="utf-8") as handle:
                content = handle.read()

        self.assertIn("PlayResX: 1080", content)
        self.assertIn("Dialogue:", content)
        self.assertIn("0:00:00.00", content)
        self.assertIn("\\{agora\\}", content)
        self.assertNotIn("-1:", content)

    def test_political_terms_use_alert_style(self):
        generator = SubtitleGenerator({"render_preset": "political_shorts"})
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "alert.ass")
            generator.generate_ass_file(
                [{
                    "start": 0,
                    "end": 1,
                    "text": "Decisão ilegal: 10 mil casos.",
                    "words": [
                        {"word": "Decisão", "start": 0, "end": 0.2},
                        {"word": "ilegal", "start": 0.2, "end": 0.5},
                        {"word": "10", "start": 0.5, "end": 0.7},
                        {"word": "mil", "start": 0.7, "end": 0.8},
                    ],
                }],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("Style: Alert", content)
        self.assertIn("{\\rAlert}{\\t(0,50,\\fscx115\\fscy115)\\t(50,150,\\fscx100\\fscy100)}ilegal", content)
        self.assertIn("{\\rAlert}{\\t(0,50,\\fscx115\\fscy115)\\t(50,150,\\fscx100\\fscy100)}10", content)

    def test_political_preset_uses_larger_bottom_safe_margin(self):
        generator = SubtitleGenerator({"render_preset": "political_shorts"})
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "political.ass")
            generator.generate_ass_file(
                [{"start": 0, "end": 1, "text": "Tese política", "words": []}],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn(",360,1\n", content)

    def test_generates_srt_with_non_negative_time(self):
        generator = SubtitleGenerator()
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "captions.srt")
            generator.generate_srt(
                [{"start": -1, "end": 1.25, "text": "Teste"}], path
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("00:00:00,000 --> 00:00:01,250", content)


if __name__ == "__main__":
    unittest.main()
