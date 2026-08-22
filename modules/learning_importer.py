"""Local import and validation for real reviewed-clip learning data.

The importer is deliberately local and boring: it never calls Campaign Hub,
uploads GitHub data, stores raw transcript/media content, or fabricates a
large dataset. It writes sanitized feature JSONL plus an aggregate-safe
manifest under FuriaClipsData.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .approved_clip_priors import DEFAULT_FEATURE_PATH, normalize_feature_record

DEFAULT_LEARNING_DIR = Path.home() / "FuriaClipsData" / "learning"
_ALLOWED_INPUTS = {".json", ".jsonl", ".csv"}


def _text(value: Any, limit: int = 160) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _row_id(row: dict[str, Any], index: int) -> str:
    raw = _text(row.get("clip_id") or row.get("editorial_key"), 128)
    if raw:
        return raw
    stable = {
        key: value for key, value in sorted(row.items())
        if key not in {"transcript", "transcription", "caption_full", "raw_text", "file_path", "path", "url", "media_url"}
    }
    digest = hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]
    return f"row_{index}_{digest}"


def _read_rows(path: Path) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]]]:
    suffix = path.suffix.lower()
    errors: list[dict[str, Any]] = []
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = []
            for line_number, row in enumerate(csv.DictReader(handle), start=2):
                rows.append((line_number, dict(row)))
            return rows, errors
    raw = path.read_text(encoding="utf-8")
    if suffix == ".jsonl":
        rows: list[tuple[int, dict[str, Any]]] = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                errors.append({"line": line_number, "clip_id": None, "reason": "invalid_json"})
                continue
            if isinstance(item, dict):
                rows.append((line_number, item))
            else:
                errors.append({"line": line_number, "clip_id": None, "reason": "row_must_be_object"})
        return rows, errors
    payload = json.loads(raw)
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items", payload.get("records", payload.get("features", [])))
    else:
        items = []
    if not isinstance(items, list):
        raise ValueError("JSON deve conter uma lista de items/records")
    rows = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            rows.append((index, item))
        else:
            errors.append({"line": index, "clip_id": None, "reason": "row_must_be_object"})
    return rows, errors


def _canonical_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    """Map common exports to the layer-3 contract without retaining raw text."""
    mapped = dict(row)
    mapped["clip_id"] = _row_id(row, index)
    mapped["label"] = row.get("label") or row.get("decision") or row.get("review_status") or row.get("action")
    mapped["duration_sec"] = row.get("duration_sec") or row.get("short_duration") or row.get("clip_duration") or row.get("duration")
    mapped["format_id"] = row.get("format_id") or row.get("format") or row.get("visual_format")
    mapped["editorial_family"] = row.get("editorial_family") or row.get("family") or row.get("hook_family") or row.get("hook")
    mapped["headline_sanitized"] = row.get("headline_sanitized") or row.get("headline") or row.get("artwork_text") or row.get("title")
    mapped["hook_text_sanitized"] = row.get("hook_text_sanitized") or row.get("hook_text") or ""
    mapped["features"] = row.get("features") if isinstance(row.get("features"), dict) else {}
    return mapped


def _validate_identity(row: dict[str, Any], *, strict: bool) -> str | None:
    supplied = _text(row.get("clip_id") or row.get("editorial_key"), 128)
    if strict and not supplied:
        return "missing_clip_id"
    return None


def _sanitized_record(row: dict[str, Any], *, index: int, strict: bool) -> tuple[dict[str, Any] | None, str | None]:
    identity_error = _validate_identity(row, strict=strict)
    if identity_error:
        return None, identity_error
    item = normalize_feature_record(_canonical_row(row, index))
    if not item:
        label = _text(row.get("label") or row.get("decision") or row.get("review_status") or row.get("action"), 24).lower()
        if label not in {"approved", "rejected"}:
            return None, "invalid_label"
        return None, "invalid_duration_or_schema"
    # Only bounded, aggregateable fields survive. Raw headline/transcript/media
    # fields are intentionally absent; headline_sanitized becomes shape only.
    return {
        "clip_id": item["clip_id"] or _row_id(row, index),
        "decision": item["decision"],
        "duration": item["duration"],
        "format_id": item["format_id"],
        "editorial_family": item["editorial_family"],
        "editorial_type": item["editorial_type"],
        "opening_pattern": item["opening_pattern"],
        "has_qa_bridge": item["has_qa_bridge"],
        "favorability_note": item["favorability_note"],
        "rejection_reason": item["rejection_reason"],
        "hook_family": item["hook_family"],
        "topic": item["topic"],
        "headline_shape": item["headline_shape"],
        "features": item["features"],
    }, None


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest(*, source_name: str, source_sha256: str, input_rows: int, accepted: list[dict[str, Any]], errors: list[dict[str, Any]], output_path: Path, deduplicated_rows: int) -> dict[str, Any]:
    approved_count = sum(1 for item in accepted if item["decision"] == "approved")
    rejected_count = sum(1 for item in accepted if item["decision"] == "rejected")
    return {
        "schema": "furia.learning.import.v2",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source_name": _text(source_name, 160),
        "source_sha256": source_sha256,
        "input_rows": input_rows,
        "accepted_rows": len(accepted),
        "accepted": len(accepted),
        "rejected_rows": len(errors),
        "errors": errors[:500],
        "deduplicated_rows": deduplicated_rows,
        "sample_size_approved": approved_count,
        "sample_size_rejected": rejected_count,
        "priors_updated": bool(accepted),
        "output_path": str(output_path),
        "store_path_hint": "FuriaClipsData/learning",
        "raw_transcript_or_media_stored": False,
        "campaign_hub_write_performed": False,
        "github_upload_performed": False,
        "notes": "Priors agregados; não é fine-tuning e não altera pesos automaticamente.",
    }


def _write_records(accepted: list[dict[str, Any]], *, output_dir: str | Path | None, source_name: str, source_sha256: str, input_rows: int, errors: list[dict[str, Any]], deduplicated_rows: int) -> dict[str, Any]:
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_LEARNING_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / "approved_clip_features.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for item in accepted:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = _manifest(
        source_name=source_name,
        source_sha256=source_sha256,
        input_rows=input_rows,
        accepted=accepted,
        errors=errors,
        output_path=output_path,
        deduplicated_rows=deduplicated_rows,
    )
    manifest_path = target_dir / "approved_clip_features.manifest.json"
    manifest_path.write_text(json.dumps({key: value for key, value in manifest.items() if key != "output_path"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def import_review_rows(rows: Iterable[dict[str, Any]], *, output_dir: str | Path | None = None, source_name: str = "inline_items", strict: bool = True) -> dict[str, Any]:
    """Import real inline rows, with deterministic last-write dedupe by clip_id."""
    candidates = list(rows or [])
    accepted_by_id: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    deduplicated = 0
    for index, row in enumerate(candidates, start=1):
        if not isinstance(row, dict):
            errors.append({"line": index, "clip_id": None, "reason": "row_must_be_object"})
            continue
        normalized, reason = _sanitized_record(row, index=index, strict=strict)
        clip_id = _row_id(row, index)
        if normalized is None:
            errors.append({"line": index, "clip_id": clip_id, "reason": reason or "invalid_row"})
            continue
        if normalized["clip_id"] in accepted_by_id:
            deduplicated += 1
        accepted_by_id[normalized["clip_id"]] = normalized
    accepted = list(accepted_by_id.values())
    digest = _sha256_bytes(json.dumps(accepted, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return _write_records(accepted, output_dir=output_dir, source_name=source_name, source_sha256=digest, input_rows=len(candidates), errors=errors, deduplicated_rows=deduplicated)


def import_review_dataset(input_path: str | Path, *, output_dir: str | Path | None = None, max_records: int = 10000, strict: bool = False) -> dict[str, Any]:
    """Validate a real CSV/JSON/JSONL export and save sanitized features."""
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("O arquivo de dataset não existe")
    if source.suffix.lower() not in _ALLOWED_INPUTS:
        raise ValueError("Formato não suportado; use CSV, JSON ou JSONL")
    try:
        limit = max(1, min(100000, int(max_records)))
    except (TypeError, ValueError):
        limit = 10000
    rows, parse_errors = _read_rows(source)
    rows = rows[:limit]
    accepted_by_id: dict[str, dict[str, Any]] = {}
    errors = list(parse_errors)
    deduplicated = 0
    for line_number, row in rows:
        normalized, reason = _sanitized_record(row, index=line_number, strict=strict)
        clip_id = _row_id(row, line_number)
        if normalized is None:
            errors.append({"line": line_number, "clip_id": clip_id, "reason": reason or "invalid_row"})
            continue
        if normalized["clip_id"] in accepted_by_id:
            deduplicated += 1
        accepted_by_id[normalized["clip_id"]] = normalized
    accepted = list(accepted_by_id.values())
    return _write_records(
        accepted,
        output_dir=output_dir,
        source_name=source.name,
        source_sha256=_sha256_bytes(source.read_bytes()),
        input_rows=len(rows) + len(parse_errors),
        errors=errors,
        deduplicated_rows=deduplicated,
    )
