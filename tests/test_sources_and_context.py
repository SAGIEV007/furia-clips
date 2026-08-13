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
