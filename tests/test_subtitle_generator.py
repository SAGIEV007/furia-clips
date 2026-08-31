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
        # ASS usa literal {\rStyle} (backslash-r), não caractere de carriage return
        self.assertIn(r"{\rAlert}ilegal", content)
        self.assertIn(r"{\rAlert}10", content)

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

    def test_generates_ass_with_custom_back_color(self):
        generator = SubtitleGenerator({
            "render_preset": "shorts",
            "subtitle_style": "word_by_word",
            "subtitle_back_color": "#FF0000",
        })
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "back.ass")
            generator.generate_ass_file(
                [{"start": 0, "end": 1, "text": "Teste", "words": []}],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        # #FF0000 (Red) in ASS BBGGRR = &H000000FF (Blue channel = FF)
        self.assertIn("&H000000FF", content)

    def test_generates_ass_with_center_lower_position(self):
        generator = SubtitleGenerator({
            "render_preset": "shorts",
            "subtitle_position": "center_lower",
        })
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "center.ass")
            generator.generate_ass_file(
                [{"start": 0, "end": 1, "text": "Teste", "words": []}],
                path,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn(",240,1\n", content)

    def test_generates_chunk_highlight_style(self):
        generator = SubtitleGenerator({
            "render_preset": "shorts",
            "subtitle_style": "chunk_highlight",
        })
        segments = [
            {
                "start": 0,
                "end": 2,
                "text": "Teste chunk highlight",
                "words": [
                    {"word": "Teste", "start": 0, "end": 0.5},
                    {"word": "chunk", "start": 0.5, "end": 1.0},
                    {"word": "highlight", "start": 1.0, "end": 1.5},
                    {"word": "extra", "start": 1.5, "end": 2.0},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "chunk.ass")
            generator.generate_ass_file(segments, path)
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("Style: ChunkHighlight", content)
        # chunk_highlight produz 1 linha por chunk (4 palavras), não por palavra
        self.assertIn("Dialogue: 0,0:00:00.00,0:00:02.00,ChunkHighlight,,0,0,0,,Teste chunk highlight extra", content)


if __name__ == "__main__":
    unittest.main()