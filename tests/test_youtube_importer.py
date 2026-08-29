import pytest

from modules.youtube_importer import YouTubeVideoSource, probe_youtube_url


def test_probe_youtube_url_extracts_video_id():
    result = probe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["platform"] == "youtube"
    assert result["source_video_id"] == "dQw4w9WgXcQ"
    assert result["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_probe_youtube_url_short_link():
    result = probe_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert result["source_video_id"] == "dQw4w9WgXcQ"


def test_probe_youtube_url_rejects_non_youtube():
    with pytest.raises(ValueError):
        probe_youtube_url("https://www.example.com/video")


def test_probe_youtube_url_rejects_invalid_id():
    with pytest.raises(ValueError):
        probe_youtube_url("https://www.youtube.com/watch?v=invalid")


def test_youtube_video_source_as_context_payload():
    source = YouTubeVideoSource(
        video_id="abc123xyz01",
        title="Test Video",
        duration=120.5,
        uploader="Test Channel",
        is_live=False,
        metadata={"language": "pt"},
    )
    payload = source.as_context_payload()
    assert payload["platform"] == "youtube"
    assert payload["source_video_id"] == "abc123xyz01"
    assert payload["source_title"] == "Test Video"
    assert payload["source_duration"] == 120.5
    assert payload["source_channel"] == "Test Channel"
    assert payload["is_live"] is False
    assert payload["language"] == "pt"
