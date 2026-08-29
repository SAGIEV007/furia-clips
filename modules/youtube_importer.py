"""Integração YouTube direta no pipeline via yt-dlp.

Fornece metadados normalizados e download de fontes públicas do YouTube.
Reusa a validação de URL pública e os tratamentos de erro do source_ingest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from modules.source_ingest import validate_public_url, _yt_dlp, SourceIngestError
from modules.source_ingest import download_public_video


class YouTubeImportError(RuntimeError):
    pass


@dataclass
class YouTubeVideoSource:
    video_id: str
    title: str = ""
    duration: float | None = None
    uploader: str = ""
    webpage_url: str = ""
    is_live: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_context_payload(self) -> dict[str, Any]:
        return {
            "platform": "youtube",
            "source_video_id": self.video_id,
            "source_url": self.webpage_url or f"https://www.youtube.com/watch?v={self.video_id}",
            "source_title": self.title,
            "source_duration": self.duration,
            "source_channel": self.uploader,
            "is_live": self.is_live,
            **self.metadata,
        }


def _extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _coerce_flag(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0 and str(value) not in {"nan", "inf", "-inf"}
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "sim", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "não", "nao", "off", "disabled"}:
        return False
    return bool(default)


def probe_youtube_url(url: str) -> dict[str, Any]:
    """Probe a YouTube URL and return a normalized source description.

    Tries real metadata via yt-dlp when available; falls back to the stub
    extraction when the environment lacks yt-dlp or the network call fails.
    """
    url = (url or "").strip()
    if "youtu" not in url.lower() and "youtube" not in url.lower():
        raise ValueError("URL do YouTube não reconhecida")
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise ValueError("Não foi possível extrair o video id da URL do YouTube")

    normalized = validate_public_url(url) if "://" in url else f"https://www.youtube.com/watch?v={video_id}"

    try:
        yt_dlp = _yt_dlp()
    except SourceIngestError:
        yt_dlp = None

    title = f"YouTube {video_id}"
    duration = None
    uploader = ""
    is_live = False
    metadata: dict[str, Any] = {}

    if yt_dlp is not None:
        try:
            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": False,
                "noplaylist": True,
            }
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(normalized, download=False)
            if isinstance(info, dict):
                title = str(info.get("title") or title)
                duration = info.get("duration")
                try:
                    duration = float(duration) if duration is not None else None
                except (TypeError, ValueError):
                    duration = None
                uploader = str(info.get("uploader") or info.get("channel") or "")
                is_live = _coerce_flag(info.get("is_live"))
                webpage_url = str(info.get("webpage_url") or normalized)
                metadata = {
                    "extractor": info.get("extractor", ""),
                    "language": info.get("language"),
                    "format_id": info.get("format_id"),
                }
                normalized = webpage_url
        except Exception:
            # Keep stub fallback on any network/extractor failure.
            pass

    return YouTubeVideoSource(
        video_id=video_id,
        title=title,
        duration=duration,
        uploader=uploader,
        webpage_url=normalized,
        is_live=is_live,
        metadata=metadata,
    ).as_context_payload()


def fetch_youtube_metadata(url: str) -> dict[str, Any]:
    """Return full metadata dict for a YouTube URL using yt-dlp.

    Raises ``YouTubeImportError`` when yt-dlp is unavailable or the source
    cannot be read.
    """
    url = (url or "").strip()
    if "youtu" not in url.lower() and "youtube" not in url.lower():
        raise ValueError("URL do YouTube não reconhecida")
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise ValueError("Não foi possível extrair o video id da URL do YouTube")
    normalized = validate_public_url(url) if "://" in url else f"https://www.youtube.com/watch?v={video_id}"

    yt_dlp = _yt_dlp()
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(normalized, download=False)
    except Exception as exc:
        raise YouTubeImportError("Não foi possível ler a fonte do YouTube") from exc

    if not isinstance(info, dict):
        raise YouTubeImportError("Resposta inesperada do yt-dlp")

    return {
        "url": normalized,
        "id": info.get("id", video_id),
        "title": info.get("title", "") or f"YouTube {video_id}",
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "webpage_url": info.get("webpage_url") or normalized,
        "extractor": info.get("extractor", ""),
        "is_live": _coerce_flag(info.get("is_live")),
        "language": info.get("language"),
        "format_id": info.get("format_id"),
        "metadata": info,
    }


def download_youtube_video(
    url: str,
    destination: str,
    progress=None,
    max_height: int = 1080,
    retries: int = 3,
    cancel_check=None,
) -> dict[str, Any]:
    """Download the best YouTube source up to the requested vertical resolution.

    Thin wrapper around ``source_ingest.download_public_video`` restricted to
    YouTube sources.
    """
    url = (url or "").strip()
    if "youtu" not in url.lower() and "youtube" not in url.lower():
        raise ValueError("URL do YouTube não reconhecida")

    result = download_public_video(
        url=url,
        destination=destination,
        progress=progress,
        max_height=max_height,
        retries=retries,
        cancel_check=cancel_check,
    )
    result.setdefault("source_id", _extract_youtube_id(url))
    return result
