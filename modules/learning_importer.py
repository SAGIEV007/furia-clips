"""Import and validate a user-provided reviewed-clip dataset.

The importer is intentionally boring and local: it does not invent records, call
Campaign Hub, upload to GitHub, or persist raw transcript/media content. It emits
sanitized JSONL features plus a manifest under FuriaClipsData/learning.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approved_clip_priors import DEFAULT_FEATURE_PATH, normalize_feature_record

DEFAULT_LEARNING_DIR = Path.home() / "FuriaClipsData" / "learning"
_ALLOWED_INPUTS = {".json", ".jsonl", ".csv"}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raw = path.read_text(encoding="utf-8")
    if suffix == ".jsonl":
        rows = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
        return rows
    payload = json.loads(raw)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        records = payload.get("records", payload.get("features", []))
        return [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []
    return []


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any, limit: int = 80) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _canonical_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map common export column names to the importer contract."""
    return {
        "decision": row.get("decision") or row.get("review_status") or row.get("action"),
        "duration": row.get("short_duration") or row.get("clip_duration") or row.get("duration"),
        "format_id": row.get("format_id") or row.get("format") or row.get("visual_format"),
        "hook_family": row.get("hook_family") or row.get("hook") or row.get("editorial_family"),
        "topic": row.get("topic") or row.get("theme") or row.get("subject"),
        "headline": row.get("headline") or row.get("artwork_text") or row.get("title"),
        "factors": row.get("factors") if isinstance(row.get("factors"), dict) else {},
    }


def _sanitized_record(row: dict[str, Any]) -> dict[str, Any] | None:
    item = normalize_feature_record(_canonical_row(row))
    if not item:
        return None
    # Keep only the fields needed by aggregate priors. In particular, no raw
    # headline, transcript, URL, media path, source title or speaker text.
    return {
        "decision": item["decision"],
        "duration": item["duration"],
        "format_id": item["format_id"],
        "hook_family": item["hook_family"],
        "topic": item["topic"],
        "headline_shape": item["headline_shape"],
        "factors": item["factors"],
    }


def import_review_dataset(
    input_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_records: int = 10000,
) -> dict[str, Any]:
    """Validate a real export and save sanitized features plus an audit manifest."""
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("O arquivo de dataset não existe")
    if source.suffix.lower() not in _ALLOWED_INPUTS:
        raise ValueError("Formato não suportado; use CSV, JSON ou JSONL")
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_LEARNING_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        limit = max(1, min(100000, int(max_records)))
    except (TypeError, ValueError):
        limit = 10000
    rows = _read_rows(source)[:limit]
    sanitized = [item for item in (_sanitized_record(row) for row in rows) if item]
    output_path = target_dir / "approved_clip_features.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for item in sanitized:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "schema": "furia.approved_clip_features.v1",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source.name[:160],
        "source_path": str(source),
        "source_sha256": _raw_sha256(source),
        "input_rows": len(rows),
        "accepted_rows": len(sanitized),
        "rejected_rows": len(rows) - len(sanitized),
        "output_path": str(output_path),
        "raw_transcript_or_media_stored": False,
        "campaign_hub_write_performed": False,
        "github_upload_performed": False,
        "notes": "Priors agregados; amostra mínima e impacto bounded continuam obrigatórios.",
    }
    manifest_path = target_dir / "approved_clip_features.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
