"""Public URL ingestion for video sources.

This module deliberately does not accept cookies, credentials, DRM bypass or
private URLs. It is a convenience layer for public sources supported by
yt-dlp, with YouTube as the primary documented target.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlparse


class SourceIngestError(RuntimeError):
    pass


BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0", "127.0.0.1", "::1"}


def normalize_public_url(url: str) -> str:
    """Return a browser-friendly public URL while keeping the input semantics.

    Users commonly paste ``www.youtube.com/...`` without the scheme.  That is
    a valid browser address but not a complete URL for ``urlparse`` or yt-dlp.
    Only a missing scheme is repaired here; explicit schemes such as ``file``
    remain untouched so the security validator can reject them.
    """
    value = str(url or "").strip()
    if value and not urlparse(value).scheme and not value.startswith("//"):
        value = f"https://{value}"
    elif value.startswith("//"):
        value = f"https:{value}"
    return value


def validate_public_url(url: str) -> str:
    value = normalize_public_url(url)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceIngestError("Informe uma URL pública http(s) válida.")
    if parsed.username or parsed.password:
        raise SourceIngestError("URLs com credenciais embutidas não são aceitas.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in BLOCKED_HOSTS or host.endswith(".local"):
        raise SourceIngestError("URLs locais ou privadas não são aceitas.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise SourceIngestError("O domínio da URL não pôde ser resolvido.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise SourceIngestError("A URL resolve para uma rede privada e foi bloqueada.")
    return value


def _yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise SourceIngestError("yt-dlp não está instalado. Execute o bootstrap novamente.") from exc
    return yt_dlp


def probe_public_url(url: str) -> dict:
    value = validate_public_url(url)
    yt_dlp = _yt_dlp()
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(value, download=False)
    except Exception as exc:
        raise SourceIngestError(f"Não foi possível ler a fonte pública: {str(exc)[:240]}") from exc
    return {
        "url": value,
        "id": info.get("id", ""),
        "title": info.get("title", "") or "Fonte pública",
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "webpage_url": info.get("webpage_url") or value,
        "extractor": info.get("extractor", ""),
        "is_live": bool(info.get("is_live")),
    }


def download_public_video(url: str, destination: str, progress=None) -> dict:
    value = validate_public_url(url)
    yt_dlp = _yt_dlp()
    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    hooks = []
    if progress:
        def hook(status):
            if status.get("status") == "downloading":
                total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
                done = status.get("downloaded_bytes") or 0
                percent = (done / total * 100) if total else None
                progress({"status": "downloading", "percent": percent, "downloaded": done, "total": total})
            elif status.get("status") == "finished":
                progress({"status": "finished", "filename": status.get("filename", "")})
        hooks.append(hook)

    options = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(target / "%(title).120B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "nooverwrites": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": hooks,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(value, download=True)
            filename = downloader.prepare_filename(info)
            output = Path(filename)
            if output.suffix.lower() != ".mp4":
                merged = output.with_suffix(".mp4")
                if merged.exists():
                    output = merged
            if not output.exists():
                candidates = sorted(target.glob(f"*[{info.get('id', '')}]*"), key=lambda p: p.stat().st_mtime, reverse=True)
                if candidates:
                    output = candidates[0]
    except Exception as exc:
        raise SourceIngestError(f"Não foi possível baixar a fonte pública: {str(exc)[:240]}") from exc

    if not output.exists() or not output.is_file():
        raise SourceIngestError("O download terminou sem produzir um arquivo de vídeo.")
    return {
        "path": str(output),
        "title": info.get("title", ""),
        "duration": info.get("duration"),
        "url": value,
        "extractor": info.get("extractor", ""),
    }
