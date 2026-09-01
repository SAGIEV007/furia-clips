"""Regression test: chunk_highlight style must emit ChunkHighlight dialogue lines."""

from modules.subtitle_generator import SubtitleGenerator


def test_chunk_highlight_emits_chunkhighlight_style():
    gen = SubtitleGenerator(settings={"subtitle_style": "chunk_highlight"})
    segments = [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "palavra1 palavra2 palavra3 palavra4 palavra5",
            "words": [
                {"start": 0.0, "end": 0.5, "word": "palavra1"},
                {"start": 0.5, "end": 1.0, "word": "palavra2"},
                {"start": 1.0, "end": 1.5, "word": "palavra3"},
                {"start": 1.5, "end": 2.0, "word": "palavra4"},
                {"start": 2.0, "end": 2.5, "word": "palavra5"},
            ],
        }
    ]
    out = gen._generate_chunk_highlight(segments)
    assert "ChunkHighlight" in out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "palavra1 palavra2 palavra3 palavra4" in lines[0]
    assert "palavra5" in lines[1]
