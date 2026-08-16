from app import _defer_context_incomplete_candidates


def test_context_incomplete_candidate_is_deferred_before_rendering():
    renderable, deferred = _defer_context_incomplete_candidates([
        {
            "start": 627.56,
            "end": 795.65,
            "duration": 168.09,
            "context_complete": False,
            "starts_mid_sentence": True,
            "starts_with_context_reference": False,
            "review_flags": {"context_complete": False},
        },
        {
            "start": 39.46,
            "end": 66.21,
            "duration": 26.75,
            "context_complete": True,
        },
    ])

    assert len(renderable) == 1
    assert renderable[0]["start"] == 39.46
    assert len(deferred) == 1
    assert deferred[0]["start"] == 627.56
    assert "contexto autossuficiente" in deferred[0]["reason"]
    assert "início possivelmente" in deferred[0]["reason"]


def test_technical_review_candidate_is_deferred_before_rendering():
    renderable, deferred = _defer_context_incomplete_candidates([
        {
            "start_time": 80,
            "end_time": 120,
            "duration": 40,
            "context_complete": True,
            "technical_gate_status": "review",
            "technical_gate_reasons": ["pergunta detectada sem ponte pergunta–resposta validada"],
            "review_flags": {"technical_gate_status": "review"},
        },
        {
            "start": 120,
            "end": 150,
            "duration": 30,
            "context_complete": True,
            "technical_gate_status": "clean",
        },
    ])

    assert len(renderable) == 1
    assert renderable[0]["start"] == 120
    assert len(deferred) == 1
    assert deferred[0]["start"] == 80
    assert deferred[0]["end"] == 120
    assert "revisão técnica editorial obrigatória" in deferred[0]["reason"]
    assert "pergunta detectada" in deferred[0]["reason"]


def test_missing_context_contract_remains_backward_compatible():
    renderable, deferred = _defer_context_incomplete_candidates([
        {"start": 0, "end": 20, "duration": 20, "text": "candidato legado"},
        {"start": 20, "end": 40, "duration": 20, "context_complete": True},
    ])

    assert len(renderable) == 2
    assert deferred == []
