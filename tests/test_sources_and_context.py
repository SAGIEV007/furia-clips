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


def test_parser_collapses_progressive_public_caption_windows_and_decodes_entities():
    text = (
        "00:00:01.000 Boa tarde, senhoras e senhores. Sejam\n"
        "00:00:02.000 Boa tarde, senhoras e senhores. Sejam bem-vindos\n"
        "00:00:03.000 bem-vindos ao programa. &gt;&gt; Pode.\n"
    )
    result = parse_transcript_text(text)
    assert result["segment_count"] == 3
    assert [segment["text"] for segment in result["segments"]] == [
        "Boa tarde, senhoras e senhores. Sejam",
        "bem-vindos",
        "ao programa. Pode.",
    ]
    assert "&gt;" not in result["full_text"]


def test_parser_does_not_drop_independent_short_reply():
    result = parse_transcript_text(
        "00:00:01.000 Você vem amanhã?\n"
        "00:00:02.000 Sim.\n"
        "00:00:03.000 A conversa continua."
    )
    assert [segment["text"] for segment in result["segments"]] == [
        "Você vem amanhã?",
        "Sim.",
        "A conversa continua.",
    ]


def test_parse_inline_timestamps_and_expand_single_segment_duration():
    inline = "00:00:00.000 Primeiro trecho completo. 00:00:12.000 Segundo trecho completo."
    parsed = parse_transcript_text(inline, duration=30)
    assert parsed["segment_count"] == 2
    assert parsed["segments"][1]["start"] == 12.0

    single = parse_transcript_text("00:00:10.000 Texto sem novo timestamp até o fim.", duration=40)
    assert single["segment_count"] == 1
    assert single["segments"][0]["end"] == 40.0


def test_editorial_context_uses_generic_focus_without_renan_reference():
    transcription = parse_transcript_text(
        "00:00:00.000 O candidato explica a proposta para reduzir a violência."
    )
    context = analyze_transcript_context(transcription)
    assert context["focus"] == "generic_political"
    assert "Renan Santos" not in context["description"]


def test_editorial_context_can_force_generic_focus_even_with_renan_reference():
    transcription = parse_transcript_text(
        "00:00:00.000 Renan Santos comenta a proposta e conclui a explicação."
    )
    context = analyze_transcript_context(transcription, focus="generic")
    assert context["focus"] == "generic_political"


def test_editorial_context_preserves_optional_speaker_confidence_and_overlap():
    transcription = {
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Você pode explicar a proposta?", "speaker": "mediador", "speaker_confidence": "0.82"},
            {"start": 1.8, "end": 5.0, "text": "A proposta é reduzir a violência.", "speaker": "convidado", "speaker_confidence": 0.61, "overlap_suspected": True},
        ]
    }
    context = analyze_transcript_context(transcription, focus="generic")
    assert context["signals"]["speaker_labeled_segments"] == 2
    assert context["signals"]["speaker_confidence_mean"] == 0.715
    assert context["signals"]["overlap_count"] == 1
    assert context["signals"]["possible_overlap"] is True


def test_editorial_context_ignores_invalid_speaker_confidence():
    transcription = {
        "segments": [{"start": 0.0, "end": 3.0, "text": "A proposta é clara.", "speaker": "desconhecido", "speaker_confidence": "invalid"}]
    }
    context = analyze_transcript_context(transcription, focus="generic")
    assert context["signals"]["speaker_labeled_segments"] == 1
    assert context["signals"]["speaker_confidence_mean"] is None


def test_download_stream_labels_distinguish_video_and_audio():
    from modules.source_ingest import _stream_label

    assert _stream_label({"vcodec": "avc1", "acodec": "none"}) == "vídeo"
    assert _stream_label({"vcodec": "none", "acodec": "opus"}) == "áudio"
    assert _stream_label({"vcodec": "avc1", "acodec": "aac"}) == "mídia"


def test_source_progress_messages_explain_multistream_and_merge_stages():
    import app as app_module

    assert "vídeo" in app_module._format_source_import_progress({
        "status": "downloading", "stream": "vídeo", "percent": 42.5,
    })
    assert "próxima etapa" in app_module._format_source_import_progress({
        "status": "stream_finished", "stream": "áudio",
    })
    assert "Unindo vídeo e áudio" in app_module._format_source_import_progress({"status": "merging"})
    assert "Arquivo final pronto" in app_module._format_source_import_progress({"status": "merge_finished"})


def test_editorial_context_marks_partial_speaker_coverage_for_review():
    from modules.editorial_context import analyze_transcript_context

    context = analyze_transcript_context({
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Qual é a proposta?", "speaker": "mediador"},
            {"start": 3.0, "end": 7.0, "text": "A proposta reduz o desperdício."},
            {"start": 7.0, "end": 11.0, "text": "Ela começa pela transparência."},
        ]
    })

    detection = context["speaker_detection"]
    assert detection["status"] == "partial"
    assert detection["coverage_ratio"] == round(1 / 3, 3)
    assert detection["review_required"] is True
    assert context["signals"]["speaker_detection_status"] == "partial"


def test_renan_participant_confidence_is_capped_without_full_diarization():
    from modules.editorial_context import analyze_transcript_context

    context = analyze_transcript_context({
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Renan Santos explica a proposta."},
            {"start": 3.0, "end": 6.0, "text": "Renan Santos apresenta os dados."},
            {"start": 6.0, "end": 9.0, "text": "Renan Santos conclui a resposta."},
        ],
    }, focus="renan")

    assert context["focus"] == "renan_santos"
    assert context["participant_confidence"] <= 0.52
    assert context["speaker_detection"]["status"] == "not_available"
