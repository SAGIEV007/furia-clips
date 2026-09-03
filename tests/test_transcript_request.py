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


def test_absolute_wall_clock_transcript_is_shifted_to_video_timeline():
    result = app_module._transcription_from_request(
        {
            "transcript_text": "18:37:54\nEntrevistador\nPergunta completa?\n18:38:04\nRenan\nResposta completa."
        },
        duration=30,
    )
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][1]["start"] == 10.0
    assert result["revisao_legenda"]["absolute_clock_offset_seconds"] == 67074.0


def test_relative_long_video_timestamps_are_not_shifted():
    result = app_module._transcription_from_request(
        {
            "transcript_text": "01:00:00.000 Contexto inicial.\n01:10:00.000 Resposta final."
        },
        duration=4200,
    )
    assert result["segments"][0]["start"] == 3600.0
    assert result["revisao_legenda"]["absolute_clock_offset_seconds"] == 0.0


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
