"""Public URL ingestion for video sources.

This module deliberately does not accept cookies, credentials, DRM bypass or
private URLs. It is a convenience layer for public sources supported by
yt-dlp, with YouTube as the primary documented target.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import time
from pathlib import Path
from urllib.parse import urlparse

from modules.cancellation import OperationCancelled
from modules.media_validation import validate_media


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
        **_common_yt_dlp_options(),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(value, download=False)
    except Exception as exc:
        raise _source_error("Não foi possível ler a fonte pública", exc) from exc
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


def _common_yt_dlp_options():
    return {
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "file_access_retries": 3,
        "continuedl": True,
        "noplaylist": True,
    }


def _source_error(prefix: str, exc: Exception) -> SourceIngestError:
    detail = str(exc)[:240]
    if "403" in detail or "Forbidden" in detail:
        return SourceIngestError(
            f"{prefix}: a fonte recusou o download (HTTP 403). "
            "O programa tentou novamente; verifique se o link é público, atualize o yt-dlp e tente outra vez."
        )
    return SourceIngestError(f"{prefix}: {detail}")


def download_public_subtitles(url: str, destination: str, progress=None, cancel_check=None) -> str | None:
    """Try public Portuguese subtitles before the expensive CPU fallback."""
    if cancel_check:
        cancel_check()
    value = validate_public_url(url)
    yt_dlp = _yt_dlp()
    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    options = {
        **_common_yt_dlp_options(),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["pt-BR", "pt", "por"],
        "subtitlesformat": "vtt/srt/best",
        "outtmpl": str(target / "%(title).120B [%(id)s].%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            if cancel_check:
                cancel_check()
            info = downloader.extract_info(value, download=True)
        if cancel_check:
            cancel_check()
        source_id = info.get("id", "")
        candidates = sorted(
            [*target.glob(f"*{source_id}*.vtt"), *target.glob(f"*{source_id}*.srt")],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            if progress:
                progress({"status": "subtitle", "filename": str(candidates[0])})
            return str(candidates[0])
        return None
    except OperationCancelled:
        raise
    except Exception as exc:
        if progress:
            progress({"status": "subtitle_error", "error": str(exc)[:240]})
        return None


def _stream_label(status: dict) -> str:
    """Return a human-readable label for a yt-dlp transfer hook."""
    info = status.get("info_dict") or {}
    vcodec = str(status.get("vcodec") or info.get("vcodec") or "").lower()
    acodec = str(status.get("acodec") or info.get("acodec") or "").lower()
    if vcodec and vcodec != "none" and (not acodec or acodec == "none"):
        return "vídeo"
    if acodec and acodec != "none" and (not vcodec or vcodec == "none"):
        return "áudio"
    return "mídia"


def download_public_video(url: str, destination: str, progress=None, max_height: int = 1080, retries: int = 3, cancel_check=None) -> dict:
    """Download the best public source up to the requested vertical resolution."""
    value = validate_public_url(url)
    yt_dlp = _yt_dlp()
    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    hooks = []
    postprocessor_hooks = []
    if progress:
        last_percent_by_stream = {}
        last_emit_by_stream = {}

        def hook(status):
            if cancel_check:
                cancel_check()
            filename = str(status.get("tmpfilename") or status.get("filename") or "stream")
            format_id = str(status.get("format_id") or (status.get("info_dict") or {}).get("format_id") or "")
            stream_key = f"{format_id}:{filename}"
            stream_label = _stream_label(status)
            if status.get("status") == "downloading":
                total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
                done = status.get("downloaded_bytes") or 0
                percent = (done / total * 100) if total else None
                now = time.monotonic()
                last_percent = last_percent_by_stream.get(stream_key)
                last_emit = last_emit_by_stream.get(stream_key, 0.0)
                should_emit = (
                    percent is None
                    or last_percent is None
                    or percent >= 100
                    or percent - last_percent >= 0.5
                    or now - last_emit >= 1.0
                )
                if should_emit:
                    last_percent_by_stream[stream_key] = percent
                    last_emit_by_stream[stream_key] = now
                    progress({
                        "status": "downloading",
                        "percent": percent,
                        "downloaded": done,
                        "total": total,
                        "stream": stream_label,
                    })
            elif status.get("status") == "finished":
                progress({"status": "stream_finished", "filename": status.get("filename", ""), "stream": stream_label})

        def postprocessor_hook(status):
            if cancel_check:
                cancel_check()
            name = str(status.get("postprocessor") or "processamento")
            if status.get("status") == "started":
                progress({"status": "merging", "postprocessor": name})
            elif status.get("status") == "finished":
                progress({"status": "merge_finished", "postprocessor": name})

        hooks.append(hook)
        postprocessor_hooks.append(postprocessor_hook)

    try:
        height_limit = max(144, min(int(max_height or 1080), 1080))
    except (TypeError, ValueError):
        height_limit = 1080

    options = {
        # Prefer the best separate video/audio streams up to 1080p. The final
        # fallback still accepts a combined stream when the extractor exposes
        # no DASH pair at or below the configured limit.
        "format": f"bv*[height<={height_limit}]+ba/b[height<={height_limit}]/b",
        "format_sort": [f"res:{height_limit}", "fps", "codec:h264", "size", "br", "asr"],
        "merge_output_format": "mp4",
        "outtmpl": str(target / "%(title).120B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "nooverwrites": True,
        "quiet": True,
        "no_warnings": True,
        **_common_yt_dlp_options(),
        "retries": max(1, min(int(retries or 3), 5)),
        "progress_hooks": hooks,
        "postprocessor_hooks": postprocessor_hooks,
    }
    max_attempts = max(1, min(int(retries or 3), 5))
    last_error = None
    output = None
    info = {}
    for attempt in range(1, max_attempts + 1):
        try:
            if cancel_check:
                cancel_check()
            if attempt > 1 and progress:
                progress({"status": "retry", "attempt": attempt, "max_attempts": max_attempts})
            with yt_dlp.YoutubeDL(options) as downloader:
                if cancel_check:
                    cancel_check()
                info = downloader.extract_info(value, download=True)
                filename = downloader.prepare_filename(info)
                output = Path(filename)
                if output.suffix.lower() != ".mp4":
                    merged = output.with_suffix(".mp4")
                    if merged.exists():
                        output = merged
                if not output.exists():
                    candidates = sorted(target.glob(f"*{info.get('id', '')}*"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if candidates:
                        output = candidates[0]
            if cancel_check:
                cancel_check()
            if output and output.exists():
                break
        except OperationCancelled:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                deadline = time.monotonic() + min(2 ** (attempt - 1), 5)
                while time.monotonic() < deadline:
                    if cancel_check:
                        cancel_check()
                    time.sleep(min(0.5, deadline - time.monotonic()))

    if last_error is not None and (not output or not output.exists()):
        raise _source_error("Não foi possível baixar a fonte pública", last_error) from last_error

    if not output.exists() or not output.is_file():
        raise SourceIngestError("O download terminou sem produzir um arquivo de vídeo.")

    source_duration = info.get("duration") if isinstance(info, dict) else None
    try:
        expected_duration = float(source_duration) if source_duration else None
    except (TypeError, ValueError):
        expected_duration = None
    validation = validate_media(
        str(output),
        expected_duration=expected_duration,
        duration_tolerance=5.0,
        require_audio=True,
        require_video=True,
    )
    if not validation.valid:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        detail = "; ".join(validation.errors)
        raise SourceIngestError(f"O arquivo baixado não passou na validação de mídia: {detail}")

    return {
        "path": str(output),
        "title": info.get("title", ""),
        "duration": info.get("duration"),
        "url": value,
        "extractor": info.get("extractor", ""),
        "max_height": height_limit,
    }


def download_public_audio(url: str, destination: str, progress=None, retries: int = 3, cancel_check=None) -> dict:
    """Download an audio-only public source for transcript-only operations.

    This deliberately does not replace ``download_public_video``: cutting still
    requires the original video. It only avoids the heavier video transfer when
    the caller explicitly requests a transcript without rendering clips.
    """
    value = validate_public_url(url)
    yt_dlp = _yt_dlp()
    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    hooks = []
    if progress:
        last_percent = {"value": None}
        last_emit = {"time": 0.0}

        def hook(status):
            if cancel_check:
                cancel_check()
            if status.get("status") != "downloading":
                if status.get("status") == "finished":
                    progress({"status": "stream_finished", "filename": status.get("filename", ""), "stream": "áudio"})
                return
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            done = status.get("downloaded_bytes") or 0
            percent = (done / total * 100) if total else None
            now = time.monotonic()
            previous = last_percent["value"]
            if percent is None or previous is None or percent >= 100 or percent - previous >= 0.5 or now - last_emit["time"] >= 1.0:
                last_percent["value"] = percent
                last_emit["time"] = now
                progress({
                    "status": "downloading",
                    "percent": percent,
                    "downloaded": done,
                    "total": total,
                    "stream": "áudio",
                })

        hooks.append(hook)

    try:
        max_attempts = max(1, min(int(retries or 3), 5))
    except (TypeError, ValueError):
        max_attempts = 3
    options = {
        **_common_yt_dlp_options(),
        "format": "ba/b",
        "outtmpl": str(target / "%(title).120B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "nooverwrites": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": hooks,
    }
    last_error = None
    output = None
    info = {}
    for attempt in range(1, max_attempts + 1):
        try:
            if cancel_check:
                cancel_check()
            if attempt > 1 and progress:
                progress({"status": "retry", "attempt": attempt, "max_attempts": max_attempts})
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(value, download=True)
                output = Path(downloader.prepare_filename(info))
                if not output.exists():
                    candidates = sorted(target.glob(f"*{info.get('id', '')}*"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if candidates:
                        output = candidates[0]
            if output and output.exists():
                break
        except OperationCancelled:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                deadline = time.monotonic() + min(2 ** (attempt - 1), 5)
                while time.monotonic() < deadline:
                    if cancel_check:
                        cancel_check()
                    time.sleep(min(0.5, deadline - time.monotonic()))

    if last_error is not None and (not output or not output.exists()):
        raise _source_error("Não foi possível baixar o áudio público", last_error) from last_error
    if not output or not output.exists() or not output.is_file():
        raise SourceIngestError("O download terminou sem produzir um arquivo de áudio.")

    validation = validate_media(str(output), expected_duration=info.get("duration"), duration_tolerance=5.0, require_audio=True, require_video=False)
    if not validation.valid:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        raise SourceIngestError(f"O áudio baixado não passou na validação de mídia: {'; '.join(validation.errors)}")

    return {
        "path": str(output),
        "title": info.get("title", ""),
        "duration": info.get("duration"),
        "url": value,
        "extractor": info.get("extractor", ""),
        "media_type": "audio",
    }
