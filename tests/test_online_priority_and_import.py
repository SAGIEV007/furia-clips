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

        def __init__(self, *args, **kwargs):
            pass

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

    def fake_download(url, destination, max_height=1080, progress=None):
        received.update({"url": url, "destination": destination, "max_height": max_height})
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
    assert app_module.current_task["active"] is False
