import pytest

from modules.editorial_context import analyze_transcript_context
from modules.source_ingest import SourceIngestError, normalize_public_url, validate_public_url
from modules.transcript_parser import parse_transcript_text


def test_parse_tactiq_preserves_timestamps_and_format():
    result = parse_transcript_text(
        "00:01:02.500 Pergunta do entrevistador?\n"
        "00:01:06.000 Resposta completa do Renan."
    )
    assert result["format"] == "tactiq"
    assert result["segments"][0]["start"] == 62.5
    assert result["segments"][0]["end"] == 66.0
    assert result["segment_count"] == 2


def test_parse_srt_and_vtt_ranges():
    srt = "1\n00:00:01,000 --> 00:00:03,500\nPrimeiro trecho.\n\n2\n00:00:04,000 --> 00:00:06,000\nSegundo trecho."
    result = parse_transcript_text(srt)
    assert result["format"] == "srt"
    assert result["segments"][0]["end"] == 3.5

    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nOlá."
    assert parse_transcript_text(vtt)["format"] == "vtt"


def test_editorial_context_detects_question_response_and_renan_signal():
    transcription = parse_transcript_text(
        "00:00:10.000 Você pode explicar a proposta?\n"
        "00:00:16.000 O Renan Santos explica a tese, a consequência e conclui."
    )
    context = analyze_transcript_context(transcription)
    assert context["focus"] == "renan_santos"
    assert context["question_count"] == 1
    assert context["qa_candidates"]
    assert context["qa_candidates"][0]["needs_question"] is True
    assert context["qa_candidates"][0]["renan_signal"] is True


def test_public_url_normalizes_browser_style_links_without_scheme():
    assert normalize_public_url("www.youtube.com/watch?v=k-LjFgh5o4Y&t") == "https://www.youtube.com/watch?v=k-LjFgh5o4Y&t"
    assert normalize_public_url("//www.youtube.com/watch?v=k-LjFgh5o4Y") == "https://www.youtube.com/watch?v=k-LjFgh5o4Y"
    assert normalize_public_url("https://www.youtube.com/watch?v=k-LjFgh5o4Y") == "https://www.youtube.com/watch?v=k-LjFgh5o4Y"


def test_public_url_rejects_local_and_non_http_sources():
    with pytest.raises(SourceIngestError):
        validate_public_url("file:///tmp/video.mp4")
    with pytest.raises(SourceIngestError):
        validate_public_url("http://127.0.0.1:3001")


def test_transcript_api_uses_canonical_parser(monkeypatch, tmp_path):
    import app as app_module

    client = app_module.app.test_client()
    response = client.post(
        "/api/transcript/parse",
        json={"text": "00:00:01.000 Fala do Renan."},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["transcription"]["segments"][0]["start"] == 1.0


def test_dialog_route_rejects_invalid_mode():
    import app as app_module

    client = app_module.app.test_client()
    response = client.post("/api/dialog/choose", json={"mode": "shell"})
    assert response.status_code == 400


def test_public_subtitles_are_detected_before_cpu_fallback(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import modules.source_ingest as source_ingest

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=True):
            subtitle = tmp_path / "Fonte [abc123].pt.vtt"
            subtitle.write_text("WEBVTT\\n\\n00:00:01.000 --> 00:00:02.000\\nResposta do Renan.\\n", encoding="utf-8")
            return {"id": "abc123"}

    monkeypatch.setattr(source_ingest, "validate_public_url", lambda value: "https://www.youtube.com/watch?v=abc123")
    monkeypatch.setattr(source_ingest, "_yt_dlp", lambda: SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    progress = []
    path = source_ingest.download_public_subtitles("https://example.com/video", str(tmp_path), progress.append)
    assert path is not None
    assert path.endswith(".vtt")
    assert progress[-1]["status"] == "subtitle"


def test_public_source_403_is_actionable():
    from modules.source_ingest import _source_error

    message = str(_source_error("Não foi possível baixar a fonte pública", RuntimeError("HTTP Error 403: Forbidden")))
    assert "HTTP 403" in message
    assert "link é público" in message
    assert "yt-dlp" in message
