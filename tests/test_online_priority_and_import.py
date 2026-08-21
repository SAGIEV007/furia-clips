from pathlib import Path
from types import SimpleNamespace


def test_automatic_transcription_prefers_gemini_before_cpu(monkeypatch, tmp_path):
    import app as app_module

    events = []
    gemini_result = {
        "transcript_segments": [
            {"start": "0:00", "end": "0:02", "text": "Resposta do Renan", "speaker": "Renan"}
        ]
    }
    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", lambda *args: gemini_result)

    class ForbiddenWhisper:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Whisper não deveria ser inicializado quando Gemini retorna segmentos")

    monkeypatch.setattr("modules.transcriber.Transcriber", ForbiddenWhisper)
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"ai_backend": "gemini", "gemini_api_key": "configured", "language": "pt"},
        lambda message, level="info": events.append((message, level)),
    )
    assert result["source"] == "gemini_video"
    assert any("Whisper CPU não será iniciado" in message for message, _ in events)


def test_automatic_transcription_reports_and_uses_cpu_only_after_gemini_failure(monkeypatch, tmp_path):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", lambda *args: None)

    class FakeWhisper:
        _engine = "faster-whisper"
        device = "cpu"

        def __init__(self, *args, **kwargs):
            pass

        def _detect_device(self):
            return "cpu"

        def transcribe(self, video_path, emit_progress=None):
            return {"segments": [{"start": 0, "end": 1, "text": "fallback"}], "full_text": "fallback", "language": "pt", "segment_count": 1}

    monkeypatch.setattr("modules.transcriber.Transcriber", FakeWhisper)
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"ai_backend": "gemini", "gemini_api_key": "configured", "language": "pt"},
        lambda message, level="info": events.append((message, level)),
    )
    assert result["source"] == "whisper"
    assert any("fallback local faster-whisper" in message for message, _ in events)


def test_source_import_passes_normalized_url_to_downloader(monkeypatch, tmp_path):
    import app as app_module

    downloaded = tmp_path / "download.mp4"
    downloaded.write_bytes(b"video")
    received = {}

    monkeypatch.setattr(app_module, "validate_public_url", lambda value: "https://www.youtube.com/watch?v=normalized")

    def fake_download(url, destination, max_height=1080, progress=None, retries=3, cancel_check=None):
        received.update({"url": url, "destination": destination, "max_height": max_height, "retries": retries})
        return {"path": str(downloaded), "title": "Teste", "duration": 1, "url": url, "extractor": "youtube"}

    monkeypatch.setattr(app_module, "download_public_video", fake_download)
    monkeypatch.setattr(app_module.threading, "Thread", lambda target, daemon=True: SimpleNamespace(start=target))
    app_module.current_task["active"] = False
    client = app_module.app.test_client()
    response = client.post(
        "/api/source/import",
        json={"url": "www.youtube.com/watch?v=original", "destination_dir": str(tmp_path), "max_height": 1080, "auto_transcribe": False},
    )
    assert response.status_code == 200
    assert received["url"] == "https://www.youtube.com/watch?v=normalized"
    assert received["max_height"] == 1080
    assert response.get_json()["job_id"]
    assert app_module.current_task["active"] is False


def test_source_import_terminal_event_is_bound_to_response_job(monkeypatch, tmp_path):
    import app as app_module

    downloaded = tmp_path / "bound-source.mp4"
    downloaded.write_bytes(b"video")
    events = []
    monkeypatch.setattr(app_module, "validate_public_url", lambda value: value)
    monkeypatch.setattr(
        app_module,
        "download_public_video",
        lambda *args, **kwargs: {"path": str(downloaded), "title": "Bound", "duration": 2, "url": "u", "extractor": "youtube"},
    )
    monkeypatch.setattr(app_module, "create_project", lambda *args, **kwargs: 992)
    monkeypatch.setattr(app_module, "emit_status", lambda status, data=None, job_id=None: events.append(("status", status, data or {}, job_id)))
    monkeypatch.setattr(app_module, "emit_progress", lambda message, level="info": events.append(("progress", message, level)))
    monkeypatch.setattr(app_module.threading, "Thread", lambda target, daemon=True: SimpleNamespace(start=target))
    app_module.current_task["active"] = False
    client = app_module.app.test_client()
    response = client.post(
        "/api/source/import",
        json={"url": "https://www.youtube.com/watch?v=bound", "destination_dir": str(tmp_path), "auto_transcribe": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["job_id"]
    complete_index = next(index for index, item in enumerate(events) if item[0] == "status" and item[1] == "source_import_complete")
    complete = events[complete_index]
    assert any(item[0] == "progress" for item in events[:complete_index])
    assert complete[3] == payload["job_id"]
    assert complete[2]["job_id"] == payload["job_id"]
    assert app_module.current_task["active"] is False


def test_source_import_reuses_confirmed_manual_transcript(monkeypatch, tmp_path):
    import app as app_module

    downloaded = tmp_path / "manual-source.mp4"
    downloaded.write_bytes(b"video")
    calls = {"subtitle": 0, "automatic": 0}
    events = []
    monkeypatch.setattr(app_module, "validate_public_url", lambda value: value)
    monkeypatch.setattr(
        app_module,
        "download_public_video",
        lambda *args, **kwargs: {"path": str(downloaded), "title": "Manual", "duration": 4, "url": "u", "extractor": "youtube"},
    )
    monkeypatch.setattr(app_module, "create_project", lambda *args, **kwargs: 991)
    monkeypatch.setattr(app_module, "save_transcription", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_module, "_save_transcription_artifacts", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "archive_transcription", lambda *args, **kwargs: {"quality": {"quality": "structurally_ok"}})
    monkeypatch.setattr(app_module, "emit_status", lambda status, data=None, job_id=None: events.append((status, data or {}, job_id)))
    monkeypatch.setattr(
        app_module,
        "download_public_subtitles",
        lambda *args, **kwargs: calls.__setitem__("subtitle", calls["subtitle"] + 1),
    )
    monkeypatch.setattr(
        app_module,
        "_transcribe_video_automatically",
        lambda *args, **kwargs: calls.__setitem__("automatic", calls["automatic"] + 1),
    )
    monkeypatch.setattr(app_module.threading, "Thread", lambda target, daemon=True: SimpleNamespace(start=target))
    app_module.current_task["active"] = False
    client = app_module.app.test_client()
    response = client.post(
        "/api/source/import",
        json={
            "url": "https://www.youtube.com/watch?v=manual",
            "destination_dir": str(tmp_path),
            "auto_transcribe": True,
            "manual_transcript": {
                "language": "pt",
                "segments": [{"start": 0, "end": 1.5, "text": "Resposta completa."}],
            },
        },
    )
    assert response.status_code == 200
    assert calls == {"subtitle": 0, "automatic": 0}
    complete = next(item for item in events if item[0] == "source_import_complete")
    assert complete[1]["transcription"]["coverage"]["status"] == "partial"
    assert app_module.current_task["active"] is False


def test_automatic_transcription_skips_gemini_when_public_subtitle_exists(monkeypatch, tmp_path):
    import app as app_module

    subtitle = tmp_path / "source.pt.vtt"
    subtitle.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nLegenda preferida.\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", lambda *args, **kwargs: calls.append("gemini"))
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"ai_backend": "gemini", "gemini_api_key": "configured", "language": "pt"},
        lambda message, level="info": calls.append(message),
        transcript_fallback_path=str(subtitle),
    )
    assert result["source"] == "public_subtitles"
    assert "gemini" not in calls


def test_public_subtitle_fallback_prevents_cpu_whisper(monkeypatch, tmp_path):
    import app as app_module

    subtitle = tmp_path / "source.pt.vtt"
    subtitle.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nResposta do Renan.\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", lambda *args: None)

    class ForbiddenWhisper:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Whisper CPU não deveria ser iniciado com VTT público válido")

    monkeypatch.setattr("modules.transcriber.Transcriber", ForbiddenWhisper)
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"ai_backend": "gemini", "gemini_api_key": "", "language": "pt"},
        lambda *args: None,
        transcript_fallback_path=str(subtitle),
    )
    assert result["source"] == "public_subtitles"
    assert result["segment_count"] == 1


def test_public_subtitle_preference_skips_gemini(monkeypatch, tmp_path):
    import app as app_module

    subtitle = tmp_path / "source.pt.vtt"
    subtitle.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nLegenda preferida.\n", encoding="utf-8")

    def forbidden_gemini(*args, **kwargs):
        raise AssertionError("Gemini não deveria ser chamado com legenda pública preferencial")

    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", forbidden_gemini)

    class ForbiddenWhisper:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Whisper não deveria ser chamado com VTT público válido")

    monkeypatch.setattr("modules.transcriber.Transcriber", ForbiddenWhisper)
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"transcription_source": "public_subtitle", "language": "pt"},
        lambda *args: None,
        transcript_fallback_path=str(subtitle),
    )
    assert result["source"] == "public_subtitles"
    assert result["segments"][0]["text"] == "Legenda preferida."


def test_whisper_preference_skips_gemini_and_public_subtitles(monkeypatch, tmp_path):
    import app as app_module

    def forbidden_gemini(*args, **kwargs):
        raise AssertionError("Gemini não deveria ser chamado com Whisper forçado")

    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", forbidden_gemini)

    class FakeWhisper:
        _engine = "faster-whisper"
        device = "cpu"

        def __init__(self, *args, **kwargs):
            pass

        def _detect_device(self):
            return "cpu"

        def transcribe(self, video_path, emit_progress=None):
            return {"segments": [{"start": 0, "end": 1, "text": "Whisper escolhido"}], "full_text": "Whisper escolhido", "language": "pt", "segment_count": 1}

    monkeypatch.setattr("modules.transcriber.Transcriber", FakeWhisper)
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {"transcription_source": "whisper", "language": "pt"},
        lambda *args: None,
        transcript_fallback_path=str(tmp_path / "ignored.vtt"),
    )
    assert result["source"] == "whisper"
    assert result["segments"][0]["text"] == "Whisper escolhido"


def test_long_cpu_video_uses_fast_model_for_discovery(monkeypatch, tmp_path):
    import app as app_module

    calls = []
    monkeypatch.setattr(app_module, "_run_gemini_video_analysis", lambda *args: None)
    monkeypatch.setattr(app_module, "_probe_video_duration_seconds", lambda path: 3600.0)

    class FakeWhisper:
        _engine = "faster-whisper"
        device = "cpu"

        def __init__(self, model_name="small", **kwargs):
            calls.append(model_name)

        def _detect_device(self):
            return "cpu"

        def transcribe(self, video_path, emit_progress=None):
            return {"segments": [], "full_text": "", "language": "pt", "segment_count": 0}

    monkeypatch.setattr("modules.transcriber.Transcriber", FakeWhisper)
    events = []
    result = app_module._transcribe_video_automatically(
        str(tmp_path / "video.mp4"),
        {
            "ai_backend": "gemini",
            "gemini_api_key": "",
            "language": "pt",
            "whisper_model": "small",
            "whisper_long_video_model": "base",
            "whisper_long_video_threshold_minutes": 45,
        },
        lambda message, level="info": events.append((message, level)),
    )
    assert result["source"] == "whisper"
    assert calls == ["small", "base"]
    assert any("modelo base" in message for message, _ in events)


def test_followup_video_analysis_is_opt_in_after_canonical_transcript():
    import app as app_module

    assert app_module._should_allow_followup_video_analysis(
        {"source": "public_subtitles"}, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_allow_followup_video_analysis(
        {"source": "whisper"}, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_allow_followup_video_analysis(
        {"source": "manual"}, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_allow_followup_video_analysis(
        {"source": "manual_confirmed"}, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_allow_followup_video_analysis(
        {"source": "manual_confirmed"}, {"gemini_manual_video_analysis": True}
    ) is True
    assert app_module._should_allow_followup_video_analysis(
        {"source": "manual"}, {"gemini_manual_video_analysis": True}
    ) is True
    assert app_module._should_allow_followup_video_analysis(
        {"source": "public_subtitles"}, {"gemini_video_analysis_with_transcript": True}
    ) is True


def test_context_worker_multimodal_request_respects_canonical_transcript_policy():
    import app as app_module

    assert app_module._should_request_editorial_context_multimodal(
        {"source": "manual_confirmed"}, True, None, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_request_editorial_context_multimodal(
        {"source": "public_subtitles"}, True, None, {"gemini_api_key": "configured"}
    ) is False
    assert app_module._should_request_editorial_context_multimodal(
        {"source": "manual_confirmed"}, True, None, {"gemini_manual_video_analysis": True}
    ) is True
    assert app_module._should_request_editorial_context_multimodal(
        {"source": "public_subtitles"}, True, {"source": "gemini_video"}, {"gemini_video_analysis_with_transcript": True}
    ) is False
    assert app_module._should_request_editorial_context_multimodal(
        {"source": "public_subtitles"}, False, None, {"gemini_video_analysis_with_transcript": True}
    ) is False


def test_followup_enrichment_does_not_call_gemini_by_default(monkeypatch):
    import app as app_module

    calls = []
    monkeypatch.setattr(
        app_module,
        "_run_gemini_video_analysis",
        lambda *args, **kwargs: calls.append(True),
    )
    result = app_module._enrich_editorial_context(
        "video.mp4",
        {"gemini_api_key": "configured"},
        {"description": "entrevista"},
        "",
        lambda *args, **kwargs: None,
        allow_video_analysis=app_module._should_allow_followup_video_analysis(
            {"source": "public_subtitles"}, {"gemini_api_key": "configured"}
        ),
    )
    assert calls == []
    assert result == {"description": "entrevista"}
