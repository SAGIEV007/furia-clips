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
