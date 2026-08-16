"""Local, human-readable editorial evidence store.

The SQLite database remains the source of truth for the application. This module
creates a parallel per-session folder so an editor or a future calibration pass
can inspect exactly which transcript, context dossier, headline candidates and
clip decisions were used. The store is deliberately outside the repository by
default and never uploads files by itself.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path.home() / "FuriaClipsData" / "editorial_sessions"


def _safe_name(value: Any, fallback: str = "session") -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip(".-_")
    return text[:100] or fallback


def _root(root: str | os.PathLike[str] | None = None) -> Path:
    return Path(root or os.environ.get("FURIA_EDITORIAL_SESSIONS_DIR") or DEFAULT_ROOT).expanduser().resolve()


def session_dir(
    project_id: Any = None,
    *,
    source_video: str = "",
    root: str | os.PathLike[str] | None = None,
) -> Path:
    if project_id not in (None, ""):
        name = f"project-{_safe_name(project_id)}"
    else:
        source_name = Path(str(source_video or "")).stem
        name = f"standalone-{_safe_name(source_name, 'context')}"
    path = _root(root) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: Any) -> str:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return str(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> str:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    return str(path)


def _record_base(project_id=None, clip_id=None, source_video="") -> dict[str, Any]:
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "clip_id": clip_id,
        "source_video": str(source_video or "")[:500],
    }


def save_transcription_bundle(
    transcription: dict[str, Any],
    *,
    project_id=None,
    source_video: str = "",
    selection_transcription: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Persist canonical and selection transcripts in the project session folder."""
    folder = session_dir(project_id, source_video=source_video)
    canonical_json = _write_json(folder / "transcription.json", transcription or {})
    canonical_text = folder / "transcription.txt"
    canonical_text.write_text(str((transcription or {}).get("full_text", "") or "") + "\n", encoding="utf-8")
    result = {"transcription_json": canonical_json, "transcription_text": str(canonical_text)}
    if isinstance(selection_transcription, dict):
        selection_json = _write_json(folder / "selection_transcription.json", selection_transcription)
        selection_text = folder / "selection_transcription.txt"
        selection_text.write_text(str(selection_transcription.get("full_text", "") or "") + "\n", encoding="utf-8")
        result.update({"selection_json": selection_json, "selection_text": str(selection_text)})
    return result


def save_context_bundle(
    context: dict[str, Any],
    *,
    transcription_provenance: dict[str, Any] | None = None,
    project_id=None,
    source_video: str = "",
) -> str:
    folder = session_dir(project_id, source_video=source_video)
    payload = {
        **_record_base(project_id=project_id, source_video=source_video),
        "transcription_provenance": transcription_provenance or {},
        "context": context or {},
    }
    return _write_json(folder / "context_latest.json", payload)


def save_headline_generation(
    request_payload: dict[str, Any],
    result: dict[str, Any],
    *,
    project_id=None,
    clip_id=None,
    source_video: str = "",
) -> str:
    folder = session_dir(project_id, source_video=source_video)
    payload = {
        **_record_base(project_id=project_id, clip_id=clip_id, source_video=source_video),
        "request": {
            "preferred_format": str(request_payload.get("preferred_format", "auto"))[:40],
            "mini_context": str(request_payload.get("mini_context", ""))[:500],
            "transcript": str(request_payload.get("transcript", ""))[:12000],
        },
        "result": result or {},
    }
    return _append_jsonl(folder / "headline_generations.jsonl", payload)


def save_headline_decision(
    decision: dict[str, Any],
    *,
    project_id=None,
    clip_id=None,
    source_video: str = "",
) -> str:
    folder = session_dir(project_id, source_video=source_video)
    payload = {**_record_base(project_id=project_id, clip_id=clip_id, source_video=source_video), **decision}
    return _append_jsonl(folder / "headline_decisions.jsonl", payload)


def save_clip_decision(
    decision: dict[str, Any],
    *,
    project_id=None,
    clip_id=None,
    source_video: str = "",
) -> str:
    folder = session_dir(project_id, source_video=source_video)
    payload = {**_record_base(project_id=project_id, clip_id=clip_id, source_video=source_video), **decision}
    return _append_jsonl(folder / "clip_decisions.jsonl", payload)


def write_session_manifest(
    *,
    project_id=None,
    source_video: str = "",
    transcription_provenance: dict[str, Any] | None = None,
    context_status: dict[str, Any] | None = None,
) -> str:
    folder = session_dir(project_id, source_video=source_video)
    payload = {
        **_record_base(project_id=project_id, source_video=source_video),
        "transcription_provenance": transcription_provenance or {},
        "context_status": context_status or {},
        "files": sorted(path.name for path in folder.iterdir() if path.is_file()),
    }
    return _write_json(folder / "manifest.json", payload)
