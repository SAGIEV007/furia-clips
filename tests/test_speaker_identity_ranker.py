from modules.editorial_ranker import EditorialRanker


TEXT = "A proposta apresenta a consequência concreta e termina com uma resposta completa."


def test_ranker_marks_unknown_speaker_for_renan_first_review():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "text": TEXT,
        "duration": 35,
        "context_complete": False,
        "payoff_complete": True,
        "speaker_identity_required": True,
        "speaker_identity_available": False,
        "speaker_identity_review_required": True,
    })

    assert result["technical_gate"]["status"] == "review"
    assert result["technical_gate"]["penalty"] >= 20
    assert any("identidade do locutor" in reason for reason in result["technical_gate"]["reasons"])
    assert result["review_flags"]["speaker_identity_review_required"] is True


def test_ranker_keeps_generic_unknown_speaker_compatible():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "text": TEXT,
        "duration": 35,
        "context_complete": True,
        "payoff_complete": True,
    })

    assert result["technical_gate"]["penalty"] == 0
    assert result["review_flags"]["speaker_identity_required"] is False
    assert result["review_flags"]["speaker_identity_review_required"] is False
