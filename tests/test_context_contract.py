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


def test_speaker_gate_blocks_only_the_confirmed_other_voice():
    """Undecided keeps the cut. Only a confirmed other speaker takes it away.

    The old contract deferred `None` too, and that is what emptied a whole run:
    nine candidates measured, nine undecided, nine discarded, zero clips. The
    contradiction was already inside the old assertion — `unmeasured` rendered
    while `unknown` did not, though neither knows who is speaking. Turning the
    measurement on was what deleted the cuts.
    """
    from app import _defer_speaker_conflicts

    renderable, deferred = _defer_speaker_conflicts([
        {"id": "renan", "start": 0, "end": 10, "speaker_verdict": {"e_o_locutor": True}},
        {"id": "other", "start": 10, "end": 20, "speaker_verdict": {"e_o_locutor": False}},
        {"id": "unknown", "start": 20, "end": 30, "speaker_verdict": {"e_o_locutor": None}},
        {"id": "unmeasured", "start": 30, "end": 40},
    ])

    assert [item["id"] for item in renderable] == ["renan", "unknown", "unmeasured"]
    assert [item["start"] for item in deferred] == [10]
    assert deferred[0]["reason"] == "voz confirmada como outro locutor"


def test_undecided_voice_is_delivered_carrying_the_doubt():
    """The doubt has to reach the editor on a clip he can watch."""
    from app import _defer_speaker_conflicts

    renderable, _ = _defer_speaker_conflicts([
        {"id": "unknown", "start": 20, "end": 30, "speaker_verdict": {"e_o_locutor": None}},
    ])

    clip = renderable[0]
    assert clip["speaker_gate_status"] == "review"
    assert clip["review_required"] is True
    assert clip["review_flags"]["speaker_identity_review_required"] is True
    assert any("voz não confirmada" in reason for reason in clip["review_reasons"])


def test_a_panel_where_the_voice_never_appears_still_delivers():
    """The real failure: a 29-minute debate *about* Renan, in which he never speaks.

    Every stretch comes back undecided, honestly so. Before this, that meant an
    empty folder and "nenhum corte reconhecido" on screen.
    """
    from app import _defer_speaker_conflicts

    candidatos = [
        {"id": f"corte{n}", "start": n * 60, "end": n * 60 + 45,
         "speaker_verdict": {"e_o_locutor": None, "motivo": "áudio não decide"}}
        for n in range(9)
    ]

    renderable, deferred = _defer_speaker_conflicts(candidatos)

    assert len(renderable) == 9, "o gate de locutor voltou a esvaziar a entrega"
    assert deferred == []
