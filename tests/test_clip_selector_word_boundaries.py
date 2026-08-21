from modules.clip_selector import ClipSelector


def _segments_with_words():
    return [
        {
            "start": 0.0,
            "end": 12.0,
            "text": "A tese começa aqui e termina agora.",
            "words": [
                {"word": "A", "start": 0.8, "end": 1.1},
                {"word": "tese", "start": 1.2, "end": 1.8},
                {"word": "começa", "start": 1.9, "end": 2.5},
                {"word": "aqui", "start": 2.6, "end": 3.0},
                {"word": "e", "start": 7.0, "end": 7.2},
                {"word": "termina", "start": 7.3, "end": 8.0},
                {"word": "agora", "start": 8.1, "end": 8.7},
            ],
        }
    ]


def test_word_boundary_refinement_snaps_both_edges_and_keeps_text_contract():
    selector = ClipSelector(min_duration=3, max_duration=60)
    clips = [{
        "start": 1.4,
        "end": 8.3,
        "duration": 6.9,
        "text": "A tese começa aqui e termina agora.",
    }]

    result = selector._refine_boundaries_with_words(clips, _segments_with_words())

    assert result[0]["start"] == 1.2
    assert result[0]["end"] == 8.7
    assert result[0]["duration"] == 7.5
    assert result[0]["word_boundary_refinement"]["applied"] is True
    assert result[0]["word_boundary_refinement"]["reason"] == "refinado_por_palavra"
    assert selector.get_candidate_diagnostics()["word_boundary_refined_count"] == 1


def test_word_boundary_refinement_does_not_move_a_badly_localized_candidate():
    selector = ClipSelector(min_duration=3, max_duration=60)
    clips = [{
        "start": 30.0,
        "end": 40.0,
        "duration": 10.0,
        "text": "Um candidato distante sem cobertura local.",
    }]

    result = selector._refine_boundaries_with_words(clips, _segments_with_words())

    assert result[0]["start"] == 30.0
    assert result[0]["end"] == 40.0
    assert result[0]["word_boundary_refinement"]["reason"] == "cobertura_insuficiente"
    assert selector.get_candidate_diagnostics()["word_boundary_review_count"] == 1


def test_word_boundary_refinement_is_safe_noop_without_word_timestamps():
    selector = ClipSelector(min_duration=3, max_duration=60)
    clips = [{"start": 1.4, "end": 8.3, "duration": 6.9, "text": "fala"}]

    result = selector._refine_boundaries_with_words(
        clips,
        [{"start": 0.0, "end": 10.0, "text": "fala", "words": []}],
    )

    assert result[0]["start"] == 1.4
    assert result[0]["end"] == 8.3
    assert result[0]["word_boundary_refinement"]["available"] is False
    assert result[0]["word_boundary_refinement"]["reason"] == "sem_timestamps_por_palavra"
    assert selector.get_candidate_diagnostics()["word_boundary_segments_available"] is False
