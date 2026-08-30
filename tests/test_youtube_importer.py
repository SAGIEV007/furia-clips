from modules.source_ingest import SourceIngestError
import math
from pathlib import Path

import pytest

from modules.youtube_importer import (
    YouTubeVideoSource,
    probe_youtube_url,
    fetch_youtube_metadata,
    download_youtube_video,
    YouTubeImportError,
    _extract_youtube_id,
)


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

def test_probe_youtube_url_shorts_link():
    result = probe_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert result["source_video_id"] == "dQw4w9WgXcQ"


def test_probe_youtube_url_live_link():
    result = probe_youtube_url("https://www.youtube.com/live/dQw4w9WgXcQ")
    assert result["source_video_id"] == "dQw4w9WgXcQ"

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


def test_extract_youtube_id_standard():
    assert _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_youtube_id_short():
    assert _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_youtube_id_embed():
    assert _extract_youtube_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_youtube_id_bare():
    assert _extract_youtube_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_probe_youtube_url_enriches_with_yt_dlp(monkeypatch):
    info = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "duration": 212,
        "uploader": "Rick Astley",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_live": False,
        "extractor": "youtube",
        "language": "en",
        "format_id": "251",
    }

    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return info

    yt_dlp = pytest.importorskip("yt_dlp")
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: yt_dlp)
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)

    result = probe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["source_title"] == "Never Gonna Give You Up"
    assert result["source_duration"] == 212
    assert result["source_channel"] == "Rick Astley"
    assert result["is_live"] is False
    assert result["extractor"] == "youtube"


def test_probe_youtube_url_falls_back_when_yt_dlp_import_missing(monkeypatch):
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: (_ for _ in ()).throw(SourceIngestError("yt-dlp não está instalado")))
    result = probe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["source_title"] == "YouTube dQw4w9WgXcQ"
    assert result["source_video_id"] == "dQw4w9WgXcQ"


def test_probe_youtube_url_falls_back_on_extractor_failure(monkeypatch):
    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            raise RuntimeError("network down")

    yt_dlp = pytest.importorskip("yt_dlp")
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: yt_dlp)
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)

    result = probe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["source_title"] == "YouTube dQw4w9WgXcQ"
    assert result["source_video_id"] == "dQw4w9WgXcQ"


def test_fetch_youtube_metadata_returns_enriched_payload(monkeypatch):
    info = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "duration": 212,
        "uploader": "Rick Astley",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_live": False,
        "extractor": "youtube",
        "language": "en",
        "format_id": "251",
    }

    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return info

    yt_dlp = pytest.importorskip("yt_dlp")
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: yt_dlp)
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)

    result = fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["title"] == "Never Gonna Give You Up"
    assert result["duration"] == 212
    assert result["uploader"] == "Rick Astley"
    assert result["is_live"] is False
    assert result["metadata"]["extractor"] == "youtube"


def test_fetch_youtube_metadata_rejects_non_youtube():
    with pytest.raises(ValueError):
        fetch_youtube_metadata("https://www.example.com/video")


def test_fetch_youtube_metadata_rejects_invalid_id():
    with pytest.raises(ValueError):
        fetch_youtube_metadata("https://www.youtube.com/watch?v=invalid")


def test_download_youtube_video_delegates(monkeypatch, tmp_path):
    destination = tmp_path / "out"
    destination.mkdir()

    def fake_download(url, destination, progress=None, max_height=1080, retries=3, cancel_check=None):
        assert "youtube" in url.lower()
        output = Path(destination) / "fake.mp4"
        output.write_bytes(b"fake")
        return {"path": str(output), "title": "Fake", "max_height": max_height}

    monkeypatch.setattr("modules.youtube_importer.download_public_video", fake_download)

    result = download_youtube_video(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        str(destination),
        max_height=720,
        retries=2,
    )
    assert result["path"].endswith("fake.mp4")
    assert result["max_height"] == 720
    assert result["source_id"] == "dQw4w9WgXcQ"


def test_download_youtube_video_rejects_non_youtube(tmp_path):
    with pytest.raises(ValueError):
        download_youtube_video("https://www.example.com/video", str(tmp_path))


def test_probe_youtube_url_includes_view_count_and_upload_date(monkeypatch):
    info = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "duration": 212,
        "uploader": "Rick Astley",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_live": False,
        "extractor": "youtube",
        "language": "en",
        "format_id": "251",
        "view_count": 1000000,
        "upload_date": "20091023",
    }

    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return info

    yt_dlp = pytest.importorskip("yt_dlp")
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: yt_dlp)
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)

    result = probe_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["view_count"] == 1000000
    assert result["upload_date"] == "20091023"


def test_fetch_youtube_metadata_includes_view_count_and_upload_date(monkeypatch):
    info = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "duration": 212,
        "uploader": "Rick Astley",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_live": False,
        "extractor": "youtube",
        "language": "en",
        "format_id": "251",
        "view_count": 1000000,
        "upload_date": "20091023",
    }

    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return info

    yt_dlp = pytest.importorskip("yt_dlp")
    monkeypatch.setattr("modules.youtube_importer._yt_dlp", lambda: yt_dlp)
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYoutubeDL)

    result = fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["view_count"] == 1000000
    assert result["upload_date"] == "20091023"
