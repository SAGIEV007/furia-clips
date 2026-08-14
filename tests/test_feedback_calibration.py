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

    assert scored["editorial_score_version"] == "v1-feedback-calibrated"
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
