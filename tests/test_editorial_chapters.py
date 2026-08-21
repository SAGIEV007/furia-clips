from modules.editorial_chapters import build_editorial_chapters


def test_build_editorial_chapters_does_not_duplicate_final_group():
    segments = [
        {"start": 0.0, "end": 20.0, "text": "Contexto inicial."},
        {"start": 20.0, "end": 40.0, "text": "Fechamento do trecho."},
    ]

    chapters = build_editorial_chapters(segments, target_seconds=15.0)

    assert len(chapters) == 2
    assert chapters[-1]["start"] == 20.0
    assert chapters[-1]["end"] == 40.0
    assert [chapter["id"] for chapter in chapters] == ["chapter-001", "chapter-002"]
