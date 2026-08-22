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
