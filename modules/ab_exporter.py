"""Aggregate-safe A/B run export for editorial candidate review.

The exporter stores only bounded candidate diagnostics under FuriaClipsData. It
never includes full transcripts, media paths, URLs, credentials, or raw
headline text. This is observability for human calibration, not model training.
"""

from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Iterable


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_project_env()

DEFAULT_AB_RUN_DIR = Path(
    os.environ.get("FURIA_AB_RUN_DIR", "")
) or (Path.home() / "FuriaClipsData" / "analyses" / "ab-runs")
ALLOWED_MODES = {"off", "prioritize", "require"}


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 100.0, default: float = 0.0) -> float:
    return round(max(minimum, min(maximum, _finite(value, default))), 3)


def _text(value: Any, limit: int = 128) -> str:
    value = str(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _safe_run_id(value: Any) -> str:
    raw = _text(value, 120)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._-")
    return safe[:100] or "run_unknown"


def _mode(value: Any) -> str:
    value = _text(value, 24).lower()
    return value if value in ALLOWED_MODES else "off"


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return _text(value, 12).lower() in {"1", "true", "yes", "sim", "on"}


def _nested_number(candidate: dict[str, Any], key: str, *parents: str) -> float | None:
    if key in candidate:
        return _bounded(candidate.get(key), 0, 100, 0)
    for parent in parents:
        value = candidate.get(parent)
        if isinstance(value, dict) and key in value:
            return _bounded(value.get(key), 0, 100, 0)
    return None


def _candidate_export(candidate: Any, index: int) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        candidate = {}
    factors = candidate.get("factors") if isinstance(candidate.get("factors"), dict) else {}
    technical = candidate.get("technical_gate") if isinstance(candidate.get("technical_gate"), dict) else {}
    scorecard = candidate.get("quality_scorecard") if isinstance(candidate.get("quality_scorecard"), dict) else {}
    favorability = candidate.get("favorability") if isinstance(candidate.get("favorability"), dict) else {}
    counterpunch = candidate.get("counterpunch") if isinstance(candidate.get("counterpunch"), dict) else {}
    acervo = candidate.get("acervo_context") if isinstance(candidate.get("acervo_context"), dict) else {}

    start = _finite(candidate.get("start", candidate.get("start_time")), 0.0)
    end = _finite(candidate.get("end", candidate.get("end_time")), 0.0)
    if end < start:
        start, end = end, start
    duration = _finite(candidate.get("duration"), end - start)
    if duration <= 0 and end > start:
        duration = end - start

    clip_id = _text(candidate.get("clip_id") or candidate.get("editorial_key"), 128)
    if not clip_id:
        clip_id = f"interval_{index}_{start:.3f}_{end:.3f}"

    coice_score = _nested_number(candidate, "signal", "coice", "counterpunch")
    coice_signal = _bool(candidate.get("coice_signal")) or _bool(candidate.get("coice"))
    if counterpunch:
        coice_signal = coice_signal or _bool(counterpunch.get("available")) and _bool(counterpunch.get("answer_complete"))
        coice_score = _nested_number(counterpunch, "signal") if coice_score is None else coice_score

    review_required = _bool(candidate.get("review_required"))
    review_required = review_required or _bool(candidate.get("speaker_review_required"))
    review_required = review_required or _text(scorecard.get("status"), 32) in {"review_required", "review"}
    review_required = review_required or _text(technical.get("status"), 32) in {"review", "weak", "blocked"}

    context_quality = candidate.get("context_quality")
    if context_quality is None:
        context_quality = factors.get("context_completeness", factors.get("completeness", scorecard.get("context_quality", 0)))

    return {
        "clip_id": clip_id,
        "start": round(max(0.0, start), 3),
        "end": round(max(0.0, end), 3),
        "duration": round(max(0.0, duration), 3),
        "score": _bounded(candidate.get("score", candidate.get("editorial_potential_score", candidate.get("total_score"))), 0, 100, 0),
        "favorability_score": _nested_number(candidate, "signal", "favorability") if candidate.get("favorability_score") is None else _bounded(candidate.get("favorability_score"), 0, 100, 0),
        "editorial_family": _text(candidate.get("editorial_family") or candidate.get("family") or factors.get("editorial_family") or "unknown", 48).lower() or "unknown",
        "coice_signal": coice_signal,
        "coice_score": coice_score,
        "from_acervo_seed": _bool(candidate.get("context_seed_only")) or _bool(candidate.get("from_acervo_seed")) or _bool(acervo.get("seed_only")),
        "review_required": review_required,
        "context_quality": _bounded(context_quality, 0, 100, 0),
        "context_gate": _bool(technical.get("context_gate", factors.get("context_gate", context_quality >= 60))),
        "payoff_gate": _bool(technical.get("payoff_gate", factors.get("payoff_gate", False))),
        "timing_gate": _bool(technical.get("timing_gate", factors.get("timing_gate", False))),
        "visual_evidence_required": _bool(technical.get("visual_evidence_required", candidate.get("visual_evidence_required"))),
    }


def build_run_export(
    *,
    run_id: Any,
    source_id: Any,
    favorability_mode: Any,
    ai_backend: Any,
    seeds_enabled: Any,
    candidates: Iterable[Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    safe_run_id = _safe_run_id(run_id)
    safe_generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    exported = [_candidate_export(candidate, index) for index, candidate in enumerate(candidates or [])]
    return {
        "schema": "furia.editorial.ab-run.v1",
        "run_id": safe_run_id,
        "source_id": _text(source_id, 128) or "unknown",
        "favorability_mode": _mode(favorability_mode),
        "ai_backend": _text(ai_backend, 32).lower() or "unknown",
        "seeds_enabled": _bool(seeds_enabled),
        "generated_at": _text(safe_generated_at, 64),
        "candidates_n": len(exported),
        "candidates": exported,
        "raw_transcript_included": False,
        "media_or_url_included": False,
    }


def export_run_candidates(
    *,
    run_id: Any,
    source_id: Any,
    favorability_mode: Any,
    ai_backend: Any,
    seeds_enabled: Any,
    candidates: Iterable[Any],
    output_dir: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Write one bounded JSON and CSV artifact and return only local metadata."""
    payload = build_run_export(
        run_id=run_id,
        source_id=source_id,
        favorability_mode=favorability_mode,
        ai_backend=ai_backend,
        seeds_enabled=seeds_enabled,
        candidates=candidates,
        generated_at=generated_at,
    )
    directory = Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_AB_RUN_DIR
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{payload['run_id']}.json"
    csv_path = directory / f"{payload['run_id']}.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = [
        "clip_id", "start", "end", "duration", "score", "favorability_score",
        "editorial_family", "coice_signal", "coice_score", "from_acervo_seed",
        "review_required", "context_quality", "context_gate", "payoff_gate",
        "timing_gate", "visual_evidence_required",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row.get(column) for column in columns} for row in payload["candidates"])
    return {
        "run_id": payload["run_id"],
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "candidates_n": payload["candidates_n"],
        "favorability_mode": payload["favorability_mode"],
        "seeds_enabled": payload["seeds_enabled"],
        "generated_at": payload["generated_at"],
    }


def load_run_export(run_id: Any, *, output_dir: str | Path | None = None) -> dict[str, Any] | None:
    path = (Path(output_dir).expanduser().resolve() if output_dir else DEFAULT_AB_RUN_DIR) / f"{_safe_run_id(run_id)}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and payload.get("schema") == "furia.editorial.ab-run.v1" else None
