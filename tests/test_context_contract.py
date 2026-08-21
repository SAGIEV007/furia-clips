from modules.editorial_context import analyze_transcript_context


def test_context_contract_exposes_setup_antecedent_payoff_and_review_reasons():
    transcription = {
        "coverage": {"status": "covered", "video_duration_seconds": 60, "segment_count": 4},
        "segments": [
            {"start": 0, "end": 4, "text": "Você acha que isso deveria acontecer?", "speaker": "jornalista"},
            {"start": 4, "end": 14, "text": "Isso é um erro grave e precisa ser enfrentado.", "speaker": "Renan"},
            {"start": 14, "end": 24, "text": "O ponto é que a população precisa entender a consequência.", "speaker": "Renan"},
            {"start": 24, "end": 30, "text": "Por isso, a resposta é mobilização.", "speaker": "Renan"},
        ],
    }

    result = analyze_transcript_context(transcription, focus="renan_santos")
    contract = result["context_contract"]

    assert contract["contract_version"] == "context-contract-v1"
    assert contract["minimum_window"]["include_question_or_setup"] is True
    assert contract["minimum_window"]["include_prior_context"] is True
    assert contract["minimum_window"]["include_payoff"] is True
    assert contract["evidence"]["qa_candidate_count"] >= 1
    assert contract["completeness_score"] < 100
    assert contract["review_required"] is True


def test_context_contract_marks_complete_speaker_coverage_when_segments_are_labeled():
    transcription = {
        "coverage": {"status": "covered", "video_duration_seconds": 24, "segment_count": 2},
        "segments": [
            {"start": 0, "end": 10, "text": "A tese é simples e clara.", "speaker": "Renan", "speaker_confidence": 0.9},
            {"start": 10, "end": 24, "text": "O resultado aparece na prática.", "speaker": "Renan", "speaker_confidence": 0.9},
        ],
    }

    result = analyze_transcript_context(transcription, focus="renan_santos")

    assert result["speaker_detection"]["status"] == "validated"
    assert result["context_contract"]["evidence"]["speaker_status"] == "validated"


def test_speaker_gate_defers_other_and_uncertain_voice_without_touching_missing_verdict():
    from app import _defer_speaker_conflicts

    renderable, deferred = _defer_speaker_conflicts([
        {"id": "renan", "start": 0, "end": 10, "speaker_verdict": {"e_o_locutor": True}},
        {"id": "other", "start": 10, "end": 20, "speaker_verdict": {"e_o_locutor": False}},
        {"id": "unknown", "start": 20, "end": 30, "speaker_verdict": {"e_o_locutor": None}},
        {"id": "unmeasured", "start": 30, "end": 40},
    ])

    assert [item["id"] for item in renderable] == ["renan", "unmeasured"]
    assert [item["start"] for item in deferred] == [10, 20]
    assert deferred[0]["reason"] == "voz confirmada como outro locutor"
    assert deferred[1]["reason"] == "voz não suficientemente identificada"
