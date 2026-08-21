"""Helpers for processing only a bounded interval of a long source video."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from typing import Any, Callable


_TIME_TOKEN = re.compile(r"^\s*(?:(?P<hours>\d+(?:[.,]\d+)?)\s*h\s*)?(?:(?P<minutes>\d+(?:[.,]\d+)?)\s*m\s*)?(?:(?P<seconds>\d+(?:[.,]\d+)?)\s*s?)?\s*$", re.IGNORECASE)


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


INTERVAL_IDENTITY_VERSION = "interval-v1"


def transcript_digest(transcription: dict[str, Any] | None) -> str:
    """Return a short stable digest of the canonical transcript content.

    The digest is provenance, not the interval identity: changing a transcript
    must create a comparable new version without making the source range look
    like a different range.
    """
    payload = transcription if isinstance(transcription, dict) else {}
    segments = []
    for item in payload.get("segments", []) or []:
        if not isinstance(item, dict):
            continue
        segments.append({
            "start": round(_number(item.get("start")) or 0.0, 3),
            "end": round(_number(item.get("end")) or 0.0, 3),
            "text": " ".join(str(item.get("text") or "").split()),
            "speaker": str(item.get("speaker") or ""),
        })
    canonical = json.dumps({
        "language": str(payload.get("language") or "pt"),
        "segments": segments,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def processing_interval_identity(
    source_video: Any,
    interval: dict[str, Any] | None,
    *,
    source_signature: str = "",
    contract_version: str = INTERVAL_IDENTITY_VERSION,
) -> str:
    """Build a stable identity for the original source and selected range.

    A temporary trimmed MP4 is deliberately excluded. When a local content
    signature exists it wins over paths, so the same source copied elsewhere
    retains its identity. Full-source and bounded-range jobs remain distinct.
    """
    scope = interval if isinstance(interval, dict) else {}
    active = bool(scope.get("active"))
    source_key = str(source_signature or "").strip().lower()
    if source_key:
        source_key = f"signature:{source_key[:64]}"
    else:
        source_key = f"path:{str(source_video or '').replace(chr(92), '/').strip().lower()}"
    start = _number(scope.get("start_seconds")) or 0.0
    end = _number(scope.get("end_seconds"))
    duration = _number(scope.get("source_duration_seconds"))
    payload = {
        "contract": str(contract_version or INTERVAL_IDENTITY_VERSION),
        "source": source_key,
        "scope": "interval" if active else "full_source",
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3) if end is not None else None,
        "source_duration_seconds": round(duration, 3) if duration is not None else None,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{contract_version}-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]}"


def parse_time_seconds(value: Any, *, field_name: str = "tempo") -> float | None:
    """Parse seconds or a human timecode such as ``5:00`` or ``1:05:30``."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (int, float)):
        result = _number(value)
        if result is None:
            raise ValueError(f"{field_name} inválido.")
        return result
    text = str(value).strip().lower().replace(",", ".")
    if ":" in text:
        parts = text.split(":")
        if len(parts) not in {2, 3} or any(not part.strip() for part in parts):
            raise ValueError(f"{field_name} deve usar segundos, mm:ss ou hh:mm:ss.")
        try:
            numbers = [float(part.strip()) for part in parts]
        except ValueError as exc:
            raise ValueError(f"{field_name} deve usar segundos, mm:ss ou hh:mm:ss.") from exc
        if len(numbers) == 2:
            minutes, seconds = numbers
            if seconds >= 60:
                raise ValueError(f"{field_name}: os segundos devem ficar entre 0 e 59.")
            return minutes * 60.0 + seconds
        hours, minutes, seconds = numbers
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"{field_name}: minutos e segundos devem ficar entre 0 e 59.")
        return hours * 3600.0 + minutes * 60.0 + seconds
    match = _TIME_TOKEN.match(text)
    if match and any(match.group(name) is not None for name in ("hours", "minutes", "seconds")):
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"{field_name}: minutos e segundos devem ficar entre 0 e 59.")
        return hours * 3600.0 + minutes * 60.0 + seconds
    result = _number(text)
    if result is None:
        raise ValueError(f"{field_name} deve usar segundos, mm:ss ou hh:mm:ss.")
    return result


def normalize_processing_interval(start: Any, end: Any, source_duration: Any) -> dict[str, Any]:
    """Validate an optional source interval against the measured media duration."""
    duration = _number(source_duration)
    start_seconds = parse_time_seconds(start, field_name="início do intervalo")
    end_seconds = parse_time_seconds(end, field_name="fim do intervalo")
    if start_seconds is None and end_seconds is None:
        known_duration = round(duration, 3) if duration is not None and duration > 0 else None
        return {
            "status": "full_source",
            "active": False,
            "source_duration_seconds": known_duration,
            "start_seconds": 0.0,
            "end_seconds": known_duration,
            "duration_seconds": known_duration,
            "offset_seconds": 0.0,
            "label": "fonte inteira",
        }
    if duration is None or duration <= 0:
        raise ValueError("Não foi possível medir a duração da fonte para validar o intervalo.")
    start_seconds = 0.0 if start_seconds is None else start_seconds
    end_seconds = duration if end_seconds is None else end_seconds
    if start_seconds < 0 or end_seconds < 0:
        raise ValueError("O intervalo não pode usar tempos negativos.")
    if start_seconds >= duration:
        raise ValueError("O início do intervalo está depois do fim da fonte.")
    if end_seconds > duration + 0.25:
        raise ValueError(f"O fim do intervalo ultrapassa a duração da fonte ({duration:.1f}s).")
    end_seconds = min(end_seconds, duration)
    if end_seconds <= start_seconds:
        raise ValueError("O fim do intervalo deve ser maior que o início.")
    if end_seconds - start_seconds < 1.0:
        raise ValueError("O intervalo precisa ter pelo menos 1 segundo.")
    return {
        "status": "interval",
        "active": True,
        "source_duration_seconds": round(duration, 3),
        "start_seconds": round(start_seconds, 3),
        "end_seconds": round(end_seconds, 3),
        "duration_seconds": round(end_seconds - start_seconds, 3),
        "offset_seconds": round(start_seconds, 3),
        "label": f"{_format_time(start_seconds)}–{_format_time(end_seconds)}",
    }


def _format_time(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def interval_source_boundary(interval: dict[str, Any]) -> dict[str, Any]:
    """Create the source-boundary contract used by selection diagnostics."""
    if not interval.get("active"):
        return {
            "status": "full_source",
            "content_start_seconds": 0.0,
            "confidence": 1.0,
            "evidence": [],
            "reason": "processamento usa a fonte inteira",
        }
    return {
        "status": "processing_interval",
        "content_start_seconds": 0.0,
        "confidence": 1.0,
        "evidence": ["operator_processing_interval"],
        "reason": "a faixa foi definida pelo operador; o pré-roll automático não desloca a timeline local",
        "processing_interval": dict(interval),
    }


def trim_transcription_to_interval(transcription: dict[str, Any], start: float, end: float) -> dict[str, Any]:
    """Keep overlapping segments and shift an original-source transcript to zero."""
    result = dict(transcription or {})
    kept = []
    for segment in (transcription or {}).get("segments", []) or []:
        if not isinstance(segment, dict):
            continue
        try:
            seg_start = float(segment.get("start", 0) or 0)
            seg_end = float(segment.get("end", seg_start) or seg_start)
        except (TypeError, ValueError):
            continue
        overlap_start = max(seg_start, start)
        overlap_end = min(seg_end, end)
        if overlap_end <= overlap_start:
            continue
        item = dict(segment)
        item["start"] = round(overlap_start - start, 3)
        item["end"] = round(overlap_end - start, 3)
        words = []
        for word in segment.get("words", []) or []:
            if not isinstance(word, dict):
                continue
            try:
                word_start = float(word.get("start", 0) or 0)
                word_end = float(word.get("end", word_start) or word_start)
            except (TypeError, ValueError):
                continue
            if word_end <= start or word_start >= end:
                continue
            normalized_word = dict(word)
            normalized_word["start"] = round(max(word_start, start) - start, 3)
            normalized_word["end"] = round(min(word_end, end) - start, 3)
            words.append(normalized_word)
        if words:
            item["words"] = words
        kept.append(item)
    result["segments"] = kept
    result["full_text"] = " ".join(str(item.get("text") or "").strip() for item in kept).strip()
    result["segment_count"] = len(kept)
    result["selection_scope"] = "processing_interval"
    result["processing_interval"] = {
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "duration_seconds": round(end - start, 3),
        "offset_seconds": round(start, 3),
    }
    return result


def trim_media_to_interval(
    source_path: str,
    start: float,
    end: float,
    *,
    emit_progress: Callable[[str, str], None] | None = None,
    cancel_check: Callable[[], Any] | None = None,
) -> str:
    """Create an accurate temporary MP4 containing only the requested range."""
    duration = max(0.0, float(end) - float(start))
    if duration <= 0:
        raise ValueError("O intervalo de mídia precisa ter duração positiva.")
    fd, output_path = tempfile.mkstemp(prefix="furia-interval-", suffix=".mp4")
    os.close(fd)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source_path), "-ss", f"{float(start):.3f}", "-t", f"{duration:.3f}",
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", output_path,
    ]
    if emit_progress:
        emit_progress(f"[Intervalo] Criando cópia de {duration:.1f}s ({_format_time(start)}–{_format_time(end)}); a fonte original não será alterada.", "info")
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        while process.poll() is None:
            if cancel_check:
                cancel_check()
            time.sleep(0.05)
        stderr = process.stderr.read() if process.stderr else ""
        if process.returncode != 0:
            raise RuntimeError(stderr.strip() or f"FFmpeg encerrou com código {process.returncode}")
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait()
        try:
            os.unlink(output_path)
        except OSError:
            pass
        raise
    if emit_progress:
        emit_progress(f"[Intervalo] Fonte de trabalho pronta: {duration:.1f}s.", "success")
    return output_path
