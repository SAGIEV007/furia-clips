from modules.source_boundary import detect_live_content_start, trim_transcription_to_live_start


def test_detects_live_greeting_after_meaningful_preroll():
    result = detect_live_content_start(
        {
            "segments": [
                {"start": 0, "end": 20, "text": "Abertura promocional."},
                {"start": 60, "end": 65, "text": "Senhoras e senhores, sejam bem-vindos ao programa."},
            ]
        },
        duration_seconds=900,
    )

    assert result["status"] == "detected"
    assert result["content_start_seconds"] == 60.0
    assert "senhoras" in result["evidence"][0]


def test_prefers_strong_live_opening_after_ambiguous_promotional_greeting():
    result = detect_live_content_start(
        {
            "segments": [
                {"start": 118.34, "end": 130.0, "text": "Senhoras e senhores, boa noite."},
                {"start": 169.5, "end": 177.0, "text": "Senhoras e senhores, sejam bem-vindos ao último análise da história."},
            ]
        },
        duration_seconds=5905,
    )

    assert result["status"] == "detected"
    assert result["content_start_seconds"] == 169.5
    assert result["strong_cues"]
    assert "preferida" in result["reason"]


def test_does_not_treat_normal_live_greeting_at_source_start_as_preroll():
    result = detect_live_content_start(
        {"segments": [{"start": 8, "end": 14, "text": "Boa noite, sejam bem-vindos."}]},
        duration_seconds=900,
    )

    assert result["status"] == "not_detected"
    assert result["content_start_seconds"] == 0.0


def test_does_not_detect_isolated_generic_greeting_after_short_delay():
    result = detect_live_content_start(
        {"segments": [{"start": 60, "end": 65, "text": "Boa noite a todos."}]},
        duration_seconds=900,
    )

    assert result["status"] == "not_detected"
    assert result["content_start_seconds"] == 0.0
    assert "genérica isolada" in result["reason"]


def test_manual_boundary_has_priority_and_is_bounded_by_duration():
    result = detect_live_content_start(
        {"segments": []},
        duration_seconds=900,
        manual_start_seconds=100,
    )

    assert result["status"] == "manual"
    assert result["content_start_seconds"] == 100.0
    assert result["confidence"] == 1.0


def test_trim_preserves_canonical_timestamps_and_archives_boundary():
    transcription = {
        "segments": [
            {"start": 0, "end": 20, "text": "Propaganda."},
            {"start": 170, "end": 180, "text": "Sejam bem-vindos à live."},
        ],
        "full_text": "Propaganda. Sejam bem-vindos à live.",
        "segment_count": 2,
        "language": "pt",
    }
    boundary = {"status": "manual", "content_start_seconds": 160.0, "confidence": 1.0}

    result = trim_transcription_to_live_start(transcription, boundary)

    assert result["segments"][0]["start"] == 170
    assert result["full_text"] == "Sejam bem-vindos à live."
    assert result["selection_scope"] == "live_content_only"
    assert result["source_boundary"] == boundary
    assert transcription["segment_count"] == 2


def test_trim_preserves_validated_transcription_coverage():
    transcription = {
        "segments": [{"start": 0, "end": 4, "text": "Abertura."}, {"start": 8, "end": 12, "text": "Conteúdo."}],
        "full_text": "Abertura. Conteúdo.",
        "coverage": {
            "status": "covered",
            "last_timestamp": 12.0,
            "end_ratio": 1.0,
            "segment_count": 2,
            "semantic_identity_verified": False,
        },
        "provenance": {"source": "whisper", "confirmed_by_editor": False},
    }
    result = trim_transcription_to_live_start(
        transcription,
        {"status": "manual", "content_start_seconds": 5.0, "confidence": 1.0},
    )

    assert result["coverage"]["status"] == "covered"
    assert result["coverage"]["last_timestamp"] == 12.0
    assert result["provenance"]["source"] == "whisper"
