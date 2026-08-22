from types import SimpleNamespace

import app as app_module


def test_transcript_text_request_is_marked_manual():
    result = app_module._transcription_from_request(
        {"transcript_text": "00:00:01.000 Uma resposta completa."},
        duration=10,
    )
    assert result["source"] == "manual"
    assert result["segment_count"] == 1


def test_transcript_segments_non_finite_timestamps_are_discarded():
    result = app_module._transcription_from_request(
        {
            "transcript_segments": [
                {"start": "nan", "end": 2.0, "text": "Segmento inválido."},
                {"start": 3.0, "end": "inf", "text": "Outro inválido."},
                {"start": 4.0, "end": 6.0, "text": "Segmento válido."},
            ],
        },
        duration=10,
    )
    assert result["segment_count"] == 2
    assert [segment["start"] for segment in result["segments"]] == [3.0, 4.0]
    assert all(
        value == value and value not in (float("inf"), float("-inf"))
        for segment in result["segments"]
        for value in (segment["start"], segment["end"])
    )


def test_legacy_transcribe_archives_manual_result_without_whisper(monkeypatch, tmp_path):
    video = tmp_path / "manual-source.mp4"
    video.write_bytes(b"video")
    events = []
    saved = []
    archived = {
        "relative_dir": "manual-source_hash",
        "quality": {"quality": "structurally_ok", "score": 100.0},
    }

    monkeypatch.setattr(app_module, "_resolve_media_input", lambda value: str(video))
    monkeypatch.setattr(app_module, "_probe_video_duration_seconds", lambda value: 10.0)
    monkeypatch.setattr(app_module, "get_all_settings", lambda: {"language": "pt", "transcription_source": "auto"})
    monkeypatch.setattr(app_module, "save_transcription", lambda *args: saved.append(args))
    monkeypatch.setattr(app_module, "archive_transcription", lambda *args, **kwargs: archived)
    monkeypatch.setattr(app_module, "emit_status", lambda status, data=None, job_id=None: events.append((status, data or {}, job_id)))
    monkeypatch.setattr(app_module, "emit_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_module, "check_current_task_cancel", lambda: None)
    monkeypatch.setattr(app_module.threading, "Thread", lambda target, daemon=True: SimpleNamespace(start=target))
    app_module.current_task["active"] = False

    response = app_module.app.test_client().post(
        "/api/process/transcribe",
        json={
            "video_path": str(video),
            "project_id": 77,
            "transcript_text": "00:00:01.000 Uma resposta completa e autossuficiente.",
            "transcript_language": "pt",
        },
    )

    assert response.status_code == 200
    assert saved and saved[0][0] == 77
    assert events and events[0][0] == "transcribe_complete"
    result = events[0][1]
    assert result["source"] == "manual"
    assert result["archive"] == archived
    assert result["quality"] == archived["quality"]
    assert result["coverage"]["video_duration_seconds"] == 10.0
    assert app_module.current_task["active"] is False


def test_empty_transcript_segments_are_not_marked_manual():
    assert app_module._transcription_from_request({"transcript_segments": []}, duration=10) is None
    assert app_module._transcription_from_request({}, duration=10) is None


def test_transcript_segments_request_is_marked_manual():
    result = app_module._transcription_from_request(
        {
            "transcript_segments": [
                {"start": 1.0, "end": 3.0, "text": "Uma resposta completa."},
            ],
        },
        duration=10,
    )
    assert result["source"] == "manual"
    assert result["segment_count"] == 1
