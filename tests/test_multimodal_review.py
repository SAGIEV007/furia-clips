from app import _attach_multimodal_editorial_review


def _multimodal(**overrides):
    payload = {
        "source_identity_status": "validated",
        "source_identity_confidence": 0.9,
        "qa_moments": [{
            "start": "00:10",
            "end": "00:25",
            "question_present": True,
            "answer_present": True,
            "renan_focus": True,
            "overlap_suspected": False,
            "reason": "pergunta seguida de resposta",
            "confidence": 0.88,
        }],
        "audio_visual_signals": [],
    }
    payload.update(overrides)
    return payload


def test_multimodal_review_attaches_evidence_without_changing_score():
    clip = {"start": 12.0, "end": 22.0, "score": 73.0}
    result = _attach_multimodal_editorial_review([clip], _multimodal())
    review = result[0]["multimodal_editorial_review"]
    assert result[0]["score"] == 73.0
    assert review["status"] == "supporting"
    assert review["review_required"] is False
    assert review["qa_evidence"][0]["overlap_seconds"] == 10.0
    assert review["identity_status"] == "validated"


def test_multimodal_question_only_and_overlap_are_review_flags_not_hard_rejects():
    clip = {"start": 12.0, "end": 22.0, "score": 61.0}
    payload = _multimodal(qa_moments=[{
        "start": "00:10",
        "end": "00:25",
        "question_present": True,
        "answer_present": False,
        "renan_focus": True,
        "overlap_suspected": True,
        "reason": "pergunta sem resposta clara e fala sobreposta",
        "confidence": 0.82,
    }])
    result = _attach_multimodal_editorial_review([clip], payload)
    review = result[0]["multimodal_editorial_review"]
    assert review["status"] == "review"
    assert "multimodal_question_only_suspected" in review["flags"]
    assert "audio_visual_overlap_suspected" in review["flags"]
    assert result[0]["score"] == 61.0


def test_multimodal_mismatch_is_refused_as_evidence():
    clip = {"start": 12.0, "end": 22.0, "score": 61.0}
    result = _attach_multimodal_editorial_review(
        [clip], _multimodal(source_identity_status="mismatch", source_identity_confidence=0.95)
    )
    review = result[0]["multimodal_editorial_review"]
    assert review["status"] == "rejected_as_evidence"
    assert review["review_required"] is True
    assert review["flags"] == ["source_identity_mismatch"]
