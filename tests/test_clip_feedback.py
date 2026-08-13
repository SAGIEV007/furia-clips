import database


def test_needs_review_feedback_is_persisted(monkeypatch, tmp_path):
    test_db = tmp_path / "furia_feedback.sqlite"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()

    project_id = database.create_project("Live de teste", "workspace/uploads/live.mp4")
    clip_id = database.save_clip(
        project_id,
        "workspace/exports/clip.mp4",
        10.0,
        52.0,
        42.0,
        viral_score=81,
    )

    database.save_clip_feedback(
        clip_id,
        "needs_review",
        note="Confirmar contexto da acusação antes de publicar.",
    )

    clips = database.get_clips(project_id)
    history = database.get_clip_feedback(clip_id)

    assert clips[0]["review_status"] == "needs_review"
    assert history[0]["action"] == "needs_review"
    assert history[0]["note"] == "Confirmar contexto da acusação antes de publicar."
