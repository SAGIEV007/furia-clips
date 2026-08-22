import database
from modules.editorial_ranker import EditorialRanker


def _build_feedback_history(monkeypatch, tmp_path, approved_count=6, rejected_count=6):
    test_db = tmp_path / "furia_calibration.sqlite"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()
    project_id = database.create_project("Calibração", "workspace/uploads/live.mp4")

    for index in range(approved_count + rejected_count):
        approved = index < approved_count
        clip_id = database.save_clip(
            project_id,
            f"workspace/exports/clip-{index}.mp4",
            index * 30.0,
            index * 30.0 + 35.0,
            35.0,
            viral_score=86 if approved else 34,
        )
        database.update_clip_editorial_score(
            clip_id,
            86 if approved else 34,
            {
                "hook": 88 if approved else 24,
                "flow": 76 if approved else 42,
                "value": 81 if approved else 38,
            },
            confidence=0.8,
        )
        database.update_clip_review_status(clip_id, "approved" if approved else "rejected")


def test_feedback_reason_coverage_exposes_context_categories_without_reclassification(monkeypatch, tmp_path):
    _build_feedback_history(monkeypatch, tmp_path)
    calibration = database.get_feedback_calibration()

    coverage = calibration["reason_coverage"]
    assert coverage["final_decision_total"] == 12
    assert coverage["explicit_reason_total"] == 0
    assert coverage["unattributed_final_decisions"] == 12
    assert coverage["categories"]["context_payoff"]["usable"] is False
    assert "decisões sem motivo" in coverage["interpretation"]


def test_ranker_ignores_text_false_feedback_eligibility():
    ranker = EditorialRanker(
        feedback_calibration={
            "eligible": "false",
            "factor_deltas": {"hook": 25},
            "reason_coverage": {
                "categories": {
                    "context_payoff": {"approved": 8, "rejected": 2, "total": 10},
                },
            },
        }
    )

    scored = ranker.score_clip({
        "text": "A verdade é que isso precisa mudar agora. A conclusão é clara.",
        "duration": 35,
        "question_detected": True,
        "context_complete": True,
        "payoff_complete": True,
    })

    assert scored["feedback_calibration"]["eligible"] is False
    assert scored["feedback_calibration"]["adjustment"] == 0.0
    assert scored["factors"]["feedback_reason_alignment"] == 50.0


def test_ranker_uses_reason_category_as_bounded_context_signal():
    calibration = {
        "eligible": True,
        "reason_coverage": {
            "categories": {
                "context_payoff": {"approved": 8, "rejected": 2, "total": 10},
                "hook": {"approved": 2, "rejected": 8, "total": 10},
                "speaker_audio": {"approved": 0, "rejected": 0, "total": 0},
                "duration": {"approved": 0, "rejected": 0, "total": 0},
            }
        },
    }
    ranker = EditorialRanker(feedback_calibration=calibration)
    context_clip = ranker.score_clip({
        "text": "A verdade é que isso precisa mudar. A conclusão é clara.",
        "duration": 35,
        "question_detected": True,
        "context_complete": True,
        "payoff_complete": True,
    })
    hook_clip = ranker.score_clip({
        "text": "Uma fala curta e direta.",
        "duration": 35,
    })

    assert context_clip["factors"]["feedback_reason_alignment"] > hook_clip["factors"]["feedback_reason_alignment"]
    assert abs(context_clip["viral_score"] - hook_clip["viral_score"]) <= 100


def test_feedback_calibration_requires_final_decision_volume(monkeypatch, tmp_path):
    _build_feedback_history(monkeypatch, tmp_path, approved_count=2, rejected_count=2)

    calibration = database.get_feedback_calibration()

    assert calibration["eligible"] is False
    assert calibration["sample_size"] == 4
    assert calibration["approved_count"] == 2
    assert calibration["rejected_count"] == 2


def test_feedback_calibration_is_eligible_and_ranker_marks_adjustment(monkeypatch, tmp_path):
    _build_feedback_history(monkeypatch, tmp_path)
    calibration = database.get_feedback_calibration()

    assert calibration["eligible"] is True
    assert calibration["score_gap"] > 0
    assert calibration["factor_deltas"]["hook"] > 0

    ranker = EditorialRanker(feedback_calibration=calibration)
    scored = ranker.score_clip({
        "text": "A verdade é que isso precisa mudar agora! O Brasil precisa de uma resposta clara.",
        "duration": 35,
        "audio_energy": 85,
    })

    assert scored["editorial_score_version"] == "v4-renan-signals"
    assert "editor_feedback_alignment" in scored["factors"]
    assert 0 <= scored["viral_score"] <= 100


def _build_legacy_duration_history(monkeypatch, tmp_path):
    test_db = tmp_path / "furia_legacy_calibration.sqlite"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()
    project_id = database.create_project("Histórico legado", "workspace/uploads/legacy.mp4")
    approved_durations = [90, 100, 110, 120, 130, 140]
    rejected_durations = [110, 120, 130, 140, 150, 160]
    for index, duration in enumerate(approved_durations + rejected_durations):
        approved = index < len(approved_durations)
        clip_id = database.save_clip(
            project_id,
            f"workspace/exports/legacy-{index}.mp4",
            index * 200.0,
            index * 200.0 + duration,
            duration,
            viral_score=68 if approved else 64,
        )
        database.update_clip_review_status(clip_id, "approved" if approved else "rejected")


def test_legacy_feedback_uses_bounded_duration_signal(monkeypatch, tmp_path):
    _build_legacy_duration_history(monkeypatch, tmp_path)

    calibration = database.get_feedback_calibration()

    assert calibration["eligible"] is True
    assert calibration["factor_deltas"] == {"duration_fit": 25.0}
    assert calibration["duration_signal"]["usable"] is True
    assert calibration["duration_signal"]["gap_seconds"] == 20.0

    ranker = EditorialRanker(feedback_calibration=calibration)
    short = ranker.score_clip({
        "text": "A verdade é que o resultado precisa ser cobrado agora.",
        "duration": 45,
    })
    long = ranker.score_clip({
        "text": "A verdade é que o resultado precisa ser cobrado agora.",
        "duration": 160,
    })

    assert short["viral_score"] > long["viral_score"]
    assert short["feedback_calibration"]["duration_signal"]["usable"] is True
    assert abs(short["feedback_calibration"]["adjustment"]) <= 6
    assert abs(long["feedback_calibration"]["adjustment"]) <= 6


def _build_origin_feedback_history(monkeypatch, tmp_path):
    test_db = tmp_path / "furia_origin_calibration.sqlite"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()
    project_id = database.create_project("Calibração por origem", "workspace/uploads/origin.mp4")
    records = (
        [("gemini_primary", True)] * 6
        + [("gemini_primary", False)] * 2
        + [("local_fallback", True)] * 2
        + [("local_fallback", False)] * 6
    )
    for index, (origin, approved) in enumerate(records):
        clip_id = database.save_clip(
            project_id,
            f"workspace/exports/origin-{index}.mp4",
            index * 30.0,
            index * 30.0 + 35.0,
            35.0,
            viral_score=82 if approved else 38,
        )
        database.update_clip_editorial_score(
            clip_id,
            82 if approved else 38,
            {"hook": 82 if approved else 34, "flow": 74 if approved else 40},
            confidence=0.85,
            review_metadata={
                "candidate_origin": origin,
                "selection_source": "gemini" if origin == "gemini_primary" else "local",
                "confidence": 0.85,
            },
        )
        database.update_clip_review_status(clip_id, "approved" if approved else "rejected")


def test_feedback_calibration_exposes_balanced_origin_deltas(monkeypatch, tmp_path):
    _build_origin_feedback_history(monkeypatch, tmp_path)

    calibration = database.get_feedback_calibration()

    assert calibration["eligible"] is True
    assert calibration["candidate_origin_deltas"]["gemini_primary"] > 0
    assert calibration["candidate_origin_deltas"]["local_fallback"] < 0
    assert calibration["origin_calibration"]["eligible"] is True
    assert all(item["sample_size"] >= 4 for item in calibration["origin_calibration"]["origins"])


def test_ranker_applies_origin_signal_as_bounded_confidence_aware_adjustment(monkeypatch, tmp_path):
    _build_origin_feedback_history(monkeypatch, tmp_path)
    calibration = database.get_feedback_calibration()
    ranker = EditorialRanker(feedback_calibration=calibration)
    base = {
        "text": "A verdade é que isso precisa mudar agora. A conclusão é clara.",
        "duration": 35,
        "audio_energy": 80,
        "confidence": 0.9,
    }

    primary = ranker.score_clip({**base, "candidate_origin": "gemini_primary"})
    fallback = ranker.score_clip({**base, "candidate_origin": "local_fallback"})

    assert primary["feedback_calibration"]["candidate_origin_adjustment"] > 0
    assert fallback["feedback_calibration"]["candidate_origin_adjustment"] < 0
    assert primary["feedback_calibration"]["candidate_origin_confidence"] == 0.9
    assert primary["viral_score"] > fallback["viral_score"]
    assert abs(primary["feedback_calibration"]["adjustment"]) <= 6
    assert abs(fallback["feedback_calibration"]["adjustment"]) <= 6


def test_origin_signal_requires_balanced_origin_sample(monkeypatch, tmp_path):
    _build_feedback_history(monkeypatch, tmp_path, approved_count=6, rejected_count=6)
    calibration = database.get_feedback_calibration()

    assert calibration["candidate_origin_deltas"] == {}
    assert calibration["origin_calibration"]["eligible"] is False
    assert calibration["origin_calibration"]["origins"] == []

    ranker = EditorialRanker(feedback_calibration=calibration)
    scored = ranker.score_clip({
        "text": "A verdade é que isso precisa mudar agora.",
        "duration": 35,
        "candidate_origin": "local_fallback",
        "confidence": 0.9,
    })
    assert scored["feedback_calibration"]["candidate_origin_adjustment"] == 0.0



def test_database_approved_clip_feature_prior_is_aggregate_only(monkeypatch, tmp_path):
    _build_feedback_history(monkeypatch, tmp_path)
    from database import get_approved_clip_feature_prior

    prior = get_approved_clip_feature_prior(min_samples=6)
    assert prior["eligible"] is True
    assert prior["approved_count"] == 6
    assert prior["rejected_count"] == 6
    assert prior["influence_scope"].startswith("aggregate-only")
    assert "transcript" not in str(prior)
    assert "file_path" not in str(prior)
