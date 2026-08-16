import app as app_module


def test_transcript_text_request_is_marked_manual():
    result = app_module._transcription_from_request(
        {"transcript_text": "00:00:01.000 Uma resposta completa."},
        duration=10,
    )
    assert result["source"] == "manual"
    assert result["provenance"]["confirmed_by_editor"] is True
    assert result["provenance"]["input_kind"] == "transcript_text"
    assert result["segment_count"] == 1


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
    assert result["provenance"]["confirmed_by_editor"] is True
    assert result["provenance"]["input_kind"] == "transcript_segments"
    assert result["segment_count"] == 1
