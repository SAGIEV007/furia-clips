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
import math
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
        "is_live": _coerce_flag(info.get("is_live")),
    }


def _coerce_bounded_int(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return max(minimum, min(int(parsed), maximum))


def _coerce_flag(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0 and math.isfinite(float(value))
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "sim", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "não", "nao", "off", "disabled"}:
        return False
    return bool(default)


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
    detail = str(exc)[:480]
    normalized = detail.lower()
    # TLS/SSL EOF - common in sandboxed environments with Cloudflare blocking datacenter IPs
    if any(marker in normalized for marker in (
        "ssl", "tls", "eof", "sslzeroreturnerror", "ssl_error_syscall",
        "unable to download api page", "openssl",
    )) and any(marker in normalized for marker in (
        "youtube", "api page", "connection has been closed", "ssl", "eof"
    )):
        return SourceIngestError(
            f"{prefix}: falha de TLS/SSL ao contatar a plataforma (Cloudflare bloqueou o IP do ambiente). "
            "Isso acontece em sandboxes/datacenters. Fora do sandbox funciona normalmente. "
            "Use upload local do arquivo MP4 como fallback - é o caminho mais previsível para renderização. "
            "Se estiver local, atualize yt-dlp com 'yt-dlp -U' e tente novamente."
        )
    if "401" in normalized or "unauthorized" in normalized:
        return SourceIngestError(
            f"{prefix}: a plataforma recusou o acesso (HTTP 401). "
            "Use uma URL pública sem login; o Furia Clips não contorna autenticação, cookies, CAPTCHA ou conteúdo privado."
        )
    if "403" in normalized or "forbidden" in normalized:
        return SourceIngestError(
            f"{prefix}: a fonte recusou o download (HTTP 403). "
            "O programa tentou novamente; verifique se o link é público, atualize o yt-dlp e tente outra fonte pública."
        )
    if "429" in normalized or "too many requests" in normalized or "rate limit" in normalized:
        return SourceIngestError(
            f"{prefix}: a plataforma limitou temporariamente as requisições (HTTP 429). "
            "Aguarde antes de tentar novamente; o programa não contorna rate limits."
        )
    if "404" in normalized or "not found" in normalized or "video unavailable" in normalized:
        return SourceIngestError(
            f"{prefix}: o vídeo ou a página não foi encontrado(a) (HTTP 404). "
            "Confirme se o endereço está completo e se o conteúdo continua público."
        )
    if any(marker in normalized for marker in (
        "timed out", "timeout", "connection reset", "connection refused",
        "temporary failure", "temporarily unavailable", "network is unreachable",
    )):
        return SourceIngestError(
            f"{prefix}: a rede ou a plataforma demorou demais para responder. "
            "As tentativas automáticas terminaram; aguarde e tente novamente, sem iniciar várias operações ao mesmo tempo."
        )
    if any(marker in normalized for marker in (
        "sign in", "login required", "members-only", "private video",
        "age-restricted", "confirm your age", "requires authentication",
    )):
        return SourceIngestError(
            f"{prefix}: o conteúdo exige login, confirmação de idade ou não é público. "
            "Use uma URL pública sem login; o Furia Clips não contorna restrições."
        )
    if "not available in your country" in normalized or "geo" in normalized and "restrict" in normalized:
        return SourceIngestError(
            f"{prefix}: a plataforma restringiu este conteúdo por região. "
            "Escolha outra fonte pública disponível para a sua região."
        )
    if any(marker in normalized for marker in ("unsupported url", "no suitable extractor", "unsupported site")):
        return SourceIngestError(
            f"{prefix}: esta plataforma ou formato ainda não é suportado pelo importador público. "
            "Use uma URL pública compatível ou importe o arquivo localmente."
        )
    return SourceIngestError(f"{prefix}: {detail or 'erro técnico sem detalhe adicional'}")


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


def _bounded_audio_language(value) -> str:
    raw = str(value or "").strip().lower()
    return "".join(char for char in raw if char.isalnum() or char in {"-", "_"})[:32]


def _audio_language_report(info: dict) -> dict:
    """Summarize selected audio language without claiming more than metadata proves."""
    requested_formats = info.get("requested_formats") if isinstance(info, dict) else None
    audio_languages = []
    for item in requested_formats or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("acodec") or "").lower() == "none":
            continue
        language = _bounded_audio_language(item.get("language") or item.get("audio_language"))
        if language:
            audio_languages.append(language)
    # For a combined format, yt-dlp may expose the selected audio metadata on
    # the top-level record. Use it only when that record demonstrably has audio;
    # never use a language field by itself as proof of the downloaded track.
    if not requested_formats and isinstance(info, dict):
        top_level = _bounded_audio_language(info.get("language") or info.get("audio_language"))
        top_acodec = str(info.get("acodec") or "").strip().lower()
        if top_level and top_acodec and top_acodec != "none":
            audio_languages.append(top_level)
    portuguese = next((lang for lang in audio_languages if lang.startswith(("pt", "por"))), None)
    if portuguese:
        return {
            "policy": "pt-BR/pt/por-first",
            "language": portuguese,
            "status": "portuguese_confirmed",
            "observed_languages": sorted(set(audio_languages))[:8],
        }
    return {
        "policy": "pt-BR/pt/por-first",
        "language": None,
        "status": "fallback_unverified" if audio_languages else "unknown",
        "observed_languages": sorted(set(audio_languages)),
    }


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
    preexisting_paths = {item.resolve() for item in target.iterdir() if item.is_file()}
    download_paths = set()
    output = None

    def remember_download_path(value):
        raw = str(value or "").strip()
        if not raw:
            return
        try:
            candidate = Path(raw).expanduser().resolve()
            if candidate.parent == target:
                download_paths.add(candidate)
        except (OSError, RuntimeError, TypeError):
            return

    def cleanup_cancelled_download():
        candidates = set(download_paths)
        if output:
            try:
                candidates.add(Path(output).expanduser().resolve())
            except (OSError, RuntimeError, TypeError):
                pass
        try:
            candidates.update(
                item.resolve()
                for item in target.iterdir()
                if item.is_file() and item.resolve() not in preexisting_paths
                and item.name.endswith((".part", ".ytdl", ".ytdl.part"))
            )
        except (OSError, RuntimeError):
            return
        for candidate in candidates:
            if candidate in preexisting_paths or candidate.parent != target:
                continue
            try:
                if candidate.is_file():
                    candidate.unlink()
            except OSError:
                continue

    hooks = []
    postprocessor_hooks = []
    if progress:
        last_percent_by_stream = {}
        last_emit_by_stream = {}

        def hook(status):
            if cancel_check:
                cancel_check()
            filename = str(status.get("tmpfilename") or status.get("filename") or "stream")
            remember_download_path(status.get("tmpfilename"))
            remember_download_path(status.get("filename"))
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
        height_limit = _coerce_bounded_int(max_height, 1080, 144, 1080)
    except (TypeError, ValueError):
        height_limit = 1080

    options = {
        # Prefer the best separate video stream plus a Portuguese-tagged audio
        # stream. Some YouTube uploads expose dubbed audio tracks; the explicit
        # preference prevents a Spanish dub from winning when the provider gives
        # us language metadata. The fallback still accepts the best public audio
        # or a combined stream when language metadata is unavailable.
        "format": (
            f"bv*[height<={height_limit}]+ba[language^=pt]/"
            f"bv*[height<={height_limit}]+ba/"
            f"b[height<={height_limit}]/b"
        ),
        "format_sort": [f"res:{height_limit}", "fps", "codec:h264", "size", "br", "asr"],
        "merge_output_format": "mp4",
        "outtmpl": str(target / "%(title).120B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": True,
        "nooverwrites": True,
        "quiet": True,
        "no_warnings": True,
        **_common_yt_dlp_options(),
        "retries": _coerce_bounded_int(retries, 3, 1, 5),
        "progress_hooks": hooks,
        "postprocessor_hooks": postprocessor_hooks,
    }
    max_attempts = _coerce_bounded_int(retries, 3, 1, 5)
    last_error = None
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
            cleanup_cancelled_download()
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
        parsed_duration = float(source_duration) if source_duration is not None else None
    except (TypeError, ValueError):
        parsed_duration = None
    expected_duration = parsed_duration if parsed_duration is not None and math.isfinite(parsed_duration) and parsed_duration > 0 else None
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

    audio_report = _audio_language_report(info)
    return {
        "path": str(output),
        "title": info.get("title", ""),
        "duration": info.get("duration"),
        "url": value,
        "extractor": info.get("extractor", ""),
        "max_height": height_limit,
        "audio_language_policy": audio_report["policy"],
        "audio_language": audio_report["language"],
        "audio_language_status": audio_report["status"],
        "audio_observed_languages": audio_report["observed_languages"],
    }
