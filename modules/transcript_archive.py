"""Persistent transcript archive and structural quality checks.

Transcripts are editorial evidence: keep the full machine-readable payload,
a human-readable timestamped copy, provenance, and a conservative quality report
outside the repository so replacing the checkout cannot erase review context.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PERSISTENT_TRANSCRIPTS_DIR


ARCHIVE_VERSION = 1


def _slug(value: str, max_length: int = 72) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_")
    return (normalized or "transcript")[:max_length]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _segment_text(segment: dict) -> str:
    return str(segment.get("text", "") or "").strip()


def format_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0.0))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remainder = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"


def validate_transcription(transcription: dict | None, duration: float | None = None) -> dict:
    """Return explainable structural checks; never claims semantic truth."""
    payload = transcription if isinstance(transcription, dict) else {}
    segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
    issues: list[str] = []
    warnings: list[str] = []
    valid_segments = []
    overlaps = 0
    backwards = 0
    empty_text = 0
    previous_end = 0.0

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            issues.append(f"segmento {index + 1} não é um objeto")
            continue
        start = _number(segment.get("start"), -1.0)
        end = _number(segment.get("end"), -1.0)
        text = _segment_text(segment)
        if start < 0 or end < 0 or end <= start:
            issues.append(f"segmento {index + 1} possui intervalo inválido")
            continue
        if start < previous_end - 0.05:
            overlaps += 1
        previous_start = _number(segments[index - 1].get("start"), start) if index and isinstance(segments[index - 1], dict) else start
        if index and start < previous_end - 0.05 and start < previous_start:
            backwards += 1
        if not text:
            empty_text += 1
        previous_end = max(previous_end, end)
        valid_segments.append({"start": start, "end": end, "text": text})

    if not valid_segments:
        issues.append("nenhum segmento timestampado válido foi encontrado")
    if empty_text:
        warnings.append(f"{empty_text} segmento(s) sem texto")
    if overlaps:
        warnings.append(f"{overlaps} sobreposição(ões) de timestamp detectada(s)")
    if backwards:
        warnings.append(f"{backwards} retrocesso(s) de timestamp detectado(s)")

    total_text = " ".join(item["text"] for item in valid_segments).strip()
    end_time = max((item["end"] for item in valid_segments), default=0.0)
    requested_duration = _number(duration, 0.0)
    if requested_duration > 0 and end_time > requested_duration * 1.05:
        issues.append("timestamps da transcrição excedem a duração da fonte informada")
    if requested_duration > 0 and end_time < requested_duration * 0.5:
        warnings.append("a transcrição cobre menos da metade da duração informada")
    if len(total_text) < 80:
        warnings.append("texto total muito curto para validar contexto editorial")

    if not valid_segments:
        score = 0.0
    else:
        score = 100.0
        score -= min(45.0, len(issues) * 20.0)
        score -= min(25.0, len(warnings) * 8.0)
        score = max(0.0, min(100.0, score))
    if issues:
        quality = "needs_attention"
    elif warnings:
        quality = "review_recommended"
    else:
        quality = "structurally_ok"

    return {
        "quality": quality,
        "score": round(score, 1),
        "segment_count": len(segments),
        "valid_segment_count": len(valid_segments),
        "text_characters": len(total_text),
        "first_timestamp": valid_segments[0]["start"] if valid_segments else None,
        "last_timestamp": end_time if valid_segments else None,
        "duration_seconds": requested_duration or None,
        "issues": issues,
        "warnings": warnings,
        "semantic_accuracy_verified": False,
    }


def _timestamped_text(segments: list[dict]) -> str:
    lines = []
    for segment in segments:
        lines.append(f"{format_timestamp(_number(segment.get('start')))} {_segment_text(segment)}".rstrip())
    return "\n".join(lines) + ("\n" if lines else "")


def archive_transcription(
    transcription: dict,
    *,
    source_video: str = "",
    source: str = "automatic",
    source_artifact: str = "",
    project_id: int | None = None,
    duration: float | None = None,
    archive_name: str = "",
) -> dict:
    """Persist a transcript and return safe relative metadata for the UI."""
    payload = dict(transcription or {})
    segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
    quality = validate_transcription(payload, duration=duration)
    identity = "|".join([
        str(source_video or "").replace("\\", "/").lower(),
        str(source or ""),
        str(project_id or ""),
        str(len(segments)),
        str(payload.get("full_text", ""))[:500],
    ])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    stem = _slug(archive_name or Path(source_video or "video").stem)
    archive_dir = Path(PERSISTENT_TRANSCRIPTS_DIR) / f"{stem}_{digest}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "archive_version": ARCHIVE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_video": str(source_video or ""),
        "source": str(source or "automatic"),
        "source_artifact": str(source_artifact or ""),
        "project_id": project_id,
        "language": payload.get("language", "pt"),
        "quality": quality,
    }
    full_text = payload.get("full_text") or " ".join(_segment_text(item) for item in segments).strip()
    payload["full_text"] = full_text
    payload["archive_metadata"] = metadata

    json_path = archive_dir / "transcript.json"
    txt_path = archive_dir / "transcript.txt"
    metadata_path = archive_dir / "metadata.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(_timestamped_text(segments), encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "archive_dir": str(archive_dir),
        "json": str(json_path),
        "text": str(txt_path),
        "metadata": str(metadata_path),
        "relative_dir": os.path.relpath(archive_dir, PERSISTENT_TRANSCRIPTS_DIR),
        "quality": quality,
    }


def list_archived_transcriptions(limit: int = 100) -> list[dict]:
    root = Path(PERSISTENT_TRANSCRIPTS_DIR)
    if not root.is_dir():
        return []
    entries = []
    for directory in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not directory.is_dir():
            continue
        metadata_path = directory / "metadata.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        transcript_path = directory / "transcript.json"
        if transcript_path.is_file():
            try:
                payload = json.loads(transcript_path.read_text(encoding="utf-8"))
                duration = (metadata.get("quality") or {}).get("duration_seconds") if isinstance(metadata.get("quality"), dict) else None
                metadata["quality"] = validate_transcription(payload, duration=duration)
                metadata["quality_revalidated"] = True
            except (OSError, ValueError, TypeError):
                metadata["quality_revalidated"] = False
        entries.append({
            **metadata,
            "relative_dir": os.path.relpath(directory, root),
            "has_json": transcript_path.is_file(),
            "has_text": (directory / "transcript.txt").is_file(),
        })
        if len(entries) >= max(1, int(limit)):
            break
    return entries
