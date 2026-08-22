from modules.editorial_chapters import build_editorial_chapters


def test_build_editorial_chapters_discards_non_finite_segments_and_false_question_flags():
    segments = [
        {"start": "nan", "end": 5.0, "text": "Ignorar este segmento.", "is_question": "true"},
        {"start": 0.0, "end": 4.0, "text": "Uma afirmação clara.", "is_question": "false"},
        {"start": 4.1, "end": 8.0, "text": "Uma pergunta?", "is_question": "true"},
    ]

    chapters = build_editorial_chapters(segments, target_seconds=15.0)

    assert len(chapters) == 1
    assert chapters[0]["start"] == 0.0
    assert chapters[0]["has_question"] is True


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
