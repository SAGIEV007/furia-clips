"""Stub de integração YouTube direta no pipeline.

Interface mínima de fonte de vídeo. Futuramente substitui/estende o fluxo
de importação pública atual para fornecer metadados normalizados e
atalhos específicos do YouTube ao pipeline do Fúria.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


def probe_youtube_url(url: str) -> dict[str, Any]:
    """Probe a YouTube URL and return a normalized source description.

    This stub does not perform network I/O yet. It only validates the
    input shape and extracts the video id when possible.
    """
    url = (url or "").strip()
    if "youtu" not in url.lower() and "youtube" not in url.lower():
        raise ValueError("URL do YouTube não reconhecida")
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise ValueError("Não foi possível extrair o video id da URL do YouTube")
    return YouTubeVideoSource(
        video_id=video_id,
        title=f"YouTube {video_id}",
        webpage_url=url if url.startswith("http") else f"https://www.youtube.com/watch?v={video_id}",
    ).as_context_payload()


def _extract_youtube_id(url: str) -> str | None:
    import re
    patterns = [
        r"(?:v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
