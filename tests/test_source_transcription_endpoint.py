from types import SimpleNamespace


def _patch_source_transcription_route(monkeypatch, tmp_path, app_module):
    monkeypatch.setattr(app_module, "validate_public_url", lambda value: "https://www.youtube.com/watch?v=normalized")
    monkeypatch.setattr(app_module, "_resolve_source_destination", lambda requested, settings: str(tmp_path))
    monkeypatch.setattr(app_module, "set_setting", lambda *args, **kwargs: None)


def test_source_transcription_url_enqueues_persistent_job_without_cuts(monkeypatch, tmp_path):
    import app as app_module

    _patch_source_transcription_route(monkeypatch, tmp_path, app_module)
    captured = {}

    def fake_submit(job_type, target, project_id=None):
        captured.update({"job_type": job_type, "target": target, "project_id": project_id})
        return {"id": "transcription-job-1", "state": "queued"}

    monkeypatch.setattr(app_module.job_manager, "submit", fake_submit)
    app_module.current_task["active"] = False
    response = app_module.app.test_client().post(
        "/api/source/transcribe",
        json={
            "url": "www.youtube.com/watch?v=original",
            "destination_dir": str(tmp_path),
            "max_height": 480,
            "transcription_source": "whisper",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["job_id"] == "transcription-job-1"
    assert payload["transcription_source"] == "whisper"
    assert payload["media_type"] == "audio"
    assert captured["job_type"] == "source_transcription"
    assert captured["project_id"] is None


def test_source_transcription_worker_archives_transcript_and_emits_no_cuts(monkeypatch, tmp_path):
    import app as app_module

    source = tmp_path / "renan-source.mp4"
    source.write_bytes(b"fake video")
    _patch_source_transcription_route(monkeypatch, tmp_path, app_module)
    captured = {}
    events = []

    def fake_submit(job_type, target, project_id=None):
        captured["target"] = target
        return {"id": "transcription-job-2", "state": "queued"}

    monkeypatch.setattr(app_module.job_manager, "submit", fake_submit)
    monkeypatch.setattr(
        app_module,
        "download_public_audio",
        lambda *args, **kwargs: {
            "path": str(source),
            "title": "Fonte Renan",
            "duration": 10,
            "url": "https://www.youtube.com/watch?v=normalized",
            "extractor": "youtube",
            "media_type": "audio",
        },
    )
    monkeypatch.setattr(app_module, "download_public_video", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("vídeo não deveria ser baixado")))
    monkeypatch.setattr(app_module, "download_public_subtitles", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        app_module,
        "_transcribe_video_automatically",
        lambda *args, **kwargs: {
            "segments": [{"start": 0, "end": 2, "text": "Resposta completa do Renan."}],
            "full_text": "Resposta completa do Renan.",
            "language": "pt",
            "segment_count": 1,
            "source": "whisper",
        },
    )
    monkeypatch.setattr(app_module, "_probe_video_duration_seconds", lambda path: 10.0)
    monkeypatch.setattr(
        app_module,
        "archive_transcription",
        lambda *args, **kwargs: {
            "relative_dir": "fonte_abc",
            "quality": {"quality": "review_recommended", "segment_count": 1},
        },
    )
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    app_module.current_task["active"] = False
    response = app_module.app.test_client().post(
        "/api/source/transcribe",
        json={"url": "https://www.youtube.com/watch?v=source", "transcription_source": "whisper"},
    )
    assert response.status_code == 200

    class FakeContext:
        job_id = "transcription-job-2"

        def check_cancel(self):
            return None

        def update(self, **kwargs):
            return kwargs

    result = captured["target"](FakeContext())
    assert result["artifacts"][0]["type"] == "transcription"
    assert result["artifacts"][0]["quality"]["quality"] == "review_recommended"
    completion = next(payload for event, payload in events if event == "source_transcription_complete")
    assert completion["transcription"]["segment_count"] == 1
    assert completion["transcription"]["coverage"]["status"] == "partial"
    assert "clips" not in completion


def test_source_transcription_rejects_non_public_url_without_enqueuing(monkeypatch, tmp_path):
    import app as app_module

    called = []
    monkeypatch.setattr(app_module.job_manager, "submit", lambda *args, **kwargs: called.append(True))
    app_module.current_task["active"] = False
    response = app_module.app.test_client().post(
        "/api/source/transcribe",
        json={"url": "file:///tmp/private-video.mp4", "destination_dir": str(tmp_path)},
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert called == []
