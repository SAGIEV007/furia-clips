import pytest

from modules.source_interval import (
    interval_source_boundary,
    normalize_processing_interval,
    parse_time_seconds,
    trim_transcription_to_interval,
)


def test_parse_time_seconds_accepts_seconds_mmss_and_hhmmss():
    assert parse_time_seconds(12.5) == 12.5
    assert parse_time_seconds("05:30") == 330.0
    assert parse_time_seconds("01:05:30") == 3930.0
    assert parse_time_seconds("5m 30s") == 330.0


def test_normalize_processing_interval_clamps_end_and_describes_offset():
    interval = normalize_processing_interval("01:00", "05:00", 600)

    assert interval["active"] is True
    assert interval["start_seconds"] == 60.0
    assert interval["end_seconds"] == 300.0
    assert interval["duration_seconds"] == 240.0
    assert interval["offset_seconds"] == 60.0


def test_normalize_processing_interval_rejects_invalid_order():
    with pytest.raises(ValueError, match="maior que o início"):
        normalize_processing_interval("05:00", "01:00", 600)


def test_full_source_boundary_is_explicit():
    interval = normalize_processing_interval(None, None, 600)
    boundary = interval_source_boundary(interval)

    assert interval["active"] is False
    assert boundary["status"] == "full_source"
    assert boundary["content_start_seconds"] == 0.0


def test_trim_transcription_to_interval_shifts_segments_and_words():
    transcription = {
        "source": "manual",
        "segments": [
            {"start": 0.0, "end": 8.0, "text": "fora", "words": []},
            {
                "start": 8.0,
                "end": 18.0,
                "text": "trecho preservado",
                "words": [{"start": 9.0, "end": 11.0, "word": "trecho"}],
            },
            {"start": 18.0, "end": 25.0, "text": "fim", "words": []},
        ],
        "full_text": "fora trecho preservado fim",
    }

    result = trim_transcription_to_interval(transcription, 10.0, 20.0)

    assert [item["text"] for item in result["segments"]] == ["trecho preservado", "fim"]
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["end"] == 8.0
    assert result["segments"][0]["words"][0]["start"] == 0.0
    assert result["segments"][0]["words"][0]["end"] == 1.0
    assert result["selection_scope"] == "processing_interval"
    assert result["processing_interval"]["offset_seconds"] == 10.0


def test_trim_media_to_interval_creates_short_working_copy(tmp_path):
    import shutil
    import subprocess
    from pathlib import Path

    from modules.source_interval import trim_media_to_interval

    source = Path(__file__).parent / "fixtures" / "sample_av.mp4"
    output = trim_media_to_interval(str(source), 0.2, 1.2)
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", output],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(probe.stdout.strip())
        assert 0.8 <= duration <= 1.3
        assert source.exists()
    finally:
        Path(output).unlink(missing_ok=True)
