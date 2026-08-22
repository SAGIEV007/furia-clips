import pytest

import database


def _clip_in_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "adjustments.sqlite"))
    database.init_db()
    project_id = database.create_project("Live de revisão", "uploads/live.mp4")
    clip_id = database.save_clip(
        project_id,
        "exports/clip.mp4",
        10.0,
        52.0,
        42.0,
        viral_score=80,
        transcript="A tese completa do trecho.",
    )
    return project_id, clip_id


def test_adjustment_is_persisted_without_mutating_canonical_clip(monkeypatch, tmp_path):
    project_id, clip_id = _clip_in_temp_db(monkeypatch, tmp_path)

    payload = database.save_clip_adjustment(
        clip_id,
        {
            "start": 12.4,
            "end": 49.8,
            "duration": 37.4,
            "boundary_adjustment": {"source": "transcript", "snapped_start": True},
        },
        note="Entrada ajustada para preservar a pergunta.",
    )

    clip = database.get_clips(project_id)[0]
    history = database.get_clip_feedback(clip_id)

    assert payload["start"] == 12.4
    assert clip["start_time"] == 10.0
    assert clip["end_time"] == 52.0
    assert clip["latest_adjustment"]["start"] == 12.4
    assert clip["latest_adjustment"]["end"] == 49.8
    assert clip["review_status"] == "needs_review"
    assert history[0]["action"] == "adjusted"
    assert history[0]["note"] == "Entrada ajustada para preservar a pergunta."


def test_adjustment_rejects_invalid_interval(monkeypatch, tmp_path):
    _, clip_id = _clip_in_temp_db(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="intervalo positivo"):
        database.save_clip_adjustment(clip_id, {"start": 20, "end": 20, "duration": 0})


def test_feedback_rejects_unknown_clip(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "missing.sqlite"))
    database.init_db()

    with pytest.raises(ValueError, match="Clip não encontrado"):
        database.save_clip_feedback(999, "approved")


def test_scene_boundary_adjustment_round_trips_through_scorecard(monkeypatch, tmp_path):
    project_id, clip_id = _clip_in_temp_db(monkeypatch, tmp_path)

    database.update_clip_editorial_score(
        clip_id,
        82,
        {"hook": 82},
        confidence=0.84,
        scene_boundary_adjustment={
            "applied": True,
            "original_start": 10.5,
            "original_end": 19.5,
            "adjusted_start": 9.0,
            "adjusted_end": 20.5,
            "direction": "outward_only",
            "private_note": "não deve persistir",
        },
    )

    clip = database.get_clips(project_id)[0]

    assert clip["scene_boundary_adjustment"] == {
        "applied": True,
        "original_start": 10.5,
        "original_end": 19.5,
        "adjusted_start": 9.0,
        "adjusted_end": 20.5,
        "direction": "outward_only",
    }
