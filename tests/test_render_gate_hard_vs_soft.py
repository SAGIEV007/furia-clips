from app import _defer_context_incomplete_candidates


def _soft_candidate(start):
    """context_complete=False with no hard structural flag set."""
    return {
        "start": start,
        "end": start + 20,
        "duration": 20,
        "context_complete": False,
        "starts_mid_sentence": False,
        "starts_with_context_reference": False,
        "overlap_suspected": False,
        "timing_ambiguous": False,
        "speaker_turn_valid": True,
    }


def test_soft_context_incomplete_candidates_are_renderable_with_review_flag():
    renderable, deferred = _defer_context_incomplete_candidates([_soft_candidate(0)])

    assert deferred == []
    assert len(renderable) == 1
    assert renderable[0]["review_required"] is True
    assert renderable[0]["post_render_review_required"] is True
    assert any("contexto autossuficiente" in reason for reason in renderable[0]["review_reasons"])


def test_hard_starts_mid_sentence_candidate_is_deferred():
    candidate = _soft_candidate(0)
    candidate["starts_mid_sentence"] = True

    renderable, deferred = _defer_context_incomplete_candidates([candidate])

    assert renderable == []
    assert len(deferred) == 1
    assert "início possivelmente no meio da frase" in deferred[0]["reason"]


def test_hard_overlap_suspected_candidate_is_deferred():
    candidate = _soft_candidate(0)
    candidate["overlap_suspected"] = True

    renderable, deferred = _defer_context_incomplete_candidates([candidate])

    assert renderable == []
    assert len(deferred) == 1
    assert "sobreposição de áudio ou timestamps" in deferred[0]["reason"]


def test_hard_timing_ambiguous_candidate_is_deferred():
    candidate = _soft_candidate(0)
    candidate["timing_ambiguous"] = True

    renderable, deferred = _defer_context_incomplete_candidates([candidate])

    assert renderable == []
    assert len(deferred) == 1
    assert "timing ambíguo" in deferred[0]["reason"]


def test_hard_invalid_speaker_turn_candidate_is_deferred():
    candidate = _soft_candidate(0)
    candidate["speaker_turn_valid"] = False

    renderable, deferred = _defer_context_incomplete_candidates([candidate])

    assert renderable == []
    assert len(deferred) == 1
    assert "locutor inválido para o corte" in deferred[0]["reason"]


def test_hard_signal_in_review_flags_fallback_is_still_deferred():
    candidate = _soft_candidate(0)
    candidate["overlap_suspected"] = False
    candidate["review_flags"] = {"overlap_suspected": True}

    renderable, deferred = _defer_context_incomplete_candidates([candidate])

    assert renderable == []
    assert len(deferred) == 1


def test_regression_all_soft_candidates_from_real_log_are_all_renderable():
    """Regression test for the "0/0 clips gerados" bug.

    In the real user log (139min video), 36 candidates produced 21
    context_complete=False deferrals with no hard structural flag set, which
    combined with the 15 quality_gate rejections (out of scope here) resulted
    in 0/0 clips rendered. None of those 21 should have been discarded before
    rendering: only human review should have been required.
    """
    candidates = [_soft_candidate(i * 30) for i in range(21)]

    renderable, deferred = _defer_context_incomplete_candidates(candidates)

    assert len(renderable) == 21
    assert len(deferred) == 0
    assert all(clip["review_required"] for clip in renderable)
