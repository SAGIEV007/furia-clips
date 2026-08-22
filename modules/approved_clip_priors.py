"""Local, aggregate-only priors from reviewed short clips.

This module is deliberately not a training loop. It accepts a portable JSON/JSONL
feature export or rows from the local database, strips raw media/transcript text,
and returns bounded aggregates for ranking and artwork copy. Raw records stay in
FuriaClipsData and are never intended for GitHub or Campaign Hub.
"""

from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path
from typing import Any, Iterable


DEFAULT_FEATURE_PATH = Path.home() / "FuriaClipsData" / "learning" / "approved_clip_features.jsonl"
ALLOWED_DECISIONS = {"approved", "rejected"}
ALLOWED_FORMATS = {"vertical_916", "square_alfinetei", "fake_tweet", "unknown"}


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed if math.isfinite(parsed) else float(default)


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 100.0, default: float = 0.0) -> float:
    return max(minimum, min(maximum, _finite(value, default)))


def _label(value: Any, limit: int = 80) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _headline_shape(headline: Any) -> dict[str, Any]:
    text = _label(headline, 240)
    normalized = text.lower()
    words = re.findall(r"[\wÀ-ÿ]+", text, flags=re.UNICODE)
    return {
        "available": bool(words),
        "word_count": min(40, len(words)),
        "character_count": min(240, len(text)),
        "question": "?" in text,
        "exclamation": "!" in text,
        "contrast": any(token in normalized for token in ("mas", "contra", "enquanto", "ou", "sem", "versus", "vs")),
        "attention_word": bool(re.search(r"\b(urgente|alerta|absurdo|atenção|atencao|impressionante|arcaico)\b", normalized)),
        "attribution": bool(re.search(r"\b(renan|ele|ela|governo|stf|lula|bolsonaro)\b", normalized)),
    }


def _normalized_headline_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _headline_shape(value)
    return {
        "available": bool(value.get("available")),
        "word_count": max(0, min(40, int(_finite(value.get("word_count"), 0)))),
        "character_count": max(0, min(240, int(_finite(value.get("character_count"), 0)))),
        "question": bool(value.get("question")),
        "exclamation": bool(value.get("exclamation")),
        "contrast": bool(value.get("contrast")),
        "attention_word": bool(value.get("attention_word")),
        "attribution": bool(value.get("attribution")),
    }


def normalize_feature_record(value: Any) -> dict[str, Any] | None:
    """Normalize one reviewed-clip feature row and discard raw text/media fields."""
    if not isinstance(value, dict):
        return None
    decision = _label(value.get("decision") or value.get("review_status"), 24).lower()
    if decision not in ALLOWED_DECISIONS:
        return None
    duration = _finite(value.get("short_duration", value.get("duration")), -1.0)
    if duration <= 0 or duration > 600:
        return None
    format_id = _label(value.get("format_id") or value.get("visual_format") or "unknown", 40)
    if format_id not in ALLOWED_FORMATS:
        format_id = "unknown"
    factors = value.get("factors") if isinstance(value.get("factors"), dict) else {}
    numeric_factors = {
        key: round(_bounded(raw, 0, 100), 2)
        for key, raw in factors.items()
        if isinstance(key, str) and len(key) <= 48 and isinstance(raw, (int, float, str)) and math.isfinite(_finite(raw, float("nan")))
    }
    shape = _normalized_headline_shape(
        value.get("headline_shape")
        if isinstance(value.get("headline_shape"), dict)
        else value.get("headline") or value.get("artwork_text") or ""
    )
    return {
        "decision": decision,
        "duration": round(duration, 3),
        "format_id": format_id,
        "hook_family": _label(value.get("hook_family") or "unknown", 60).lower() or "unknown",
        "topic": _label(value.get("topic") or "unknown", 80).lower() or "unknown",
        "headline_shape": shape,
        "factors": numeric_factors,
    }


def load_feature_records(path: str | Path | None = None, *, limit: int = 5000) -> list[dict[str, Any]]:
    """Load a local JSON array, object with records, or JSONL export."""
    target = Path(path).expanduser() if path else DEFAULT_FEATURE_PATH
    try:
        raw_text = target.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return []
    if not raw_text.strip():
        return []
    raw_records: list[Any] = []
    try:
        payload = json.loads(raw_text)
        if isinstance(payload, list):
            raw_records = payload
        elif isinstance(payload, dict):
            raw_records = payload.get("records", payload.get("features", [])) if isinstance(payload.get("records", payload.get("features", [])), list) else []
    except json.JSONDecodeError:
        for line in raw_text.splitlines():
            try:
                raw_records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return [record for record in (normalize_feature_record(item) for item in raw_records[: max(1, int(limit))]) if record]


def build_feature_prior(records: Iterable[dict[str, Any]] | None, *, min_samples: int = 12) -> dict[str, Any]:
    """Return aggregate-only priors; no raw headline, transcript or media is retained."""
    normalized = [item for item in (normalize_feature_record(row) for row in (records or [])) if item]
    approved = [item for item in normalized if item["decision"] == "approved"]
    rejected = [item for item in normalized if item["decision"] == "rejected"]
    eligible = len(approved) >= max(3, int(min_samples)) and len(rejected) >= 3

    def mean(rows: list[dict[str, Any]], key: str) -> float:
        values = [_finite(item.get(key), 0.0) for item in rows if _finite(item.get(key), -1.0) >= 0]
        return round(sum(values) / len(values), 2) if values else 0.0

    def format_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in rows:
            key = item["format_id"]
            counts[key] = counts.get(key, 0) + 1
        return counts

    def family_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in rows:
            key = item["hook_family"]
            counts[key] = counts.get(key, 0) + 1
        return counts

    def shape_rate(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return 0.0
        return round(sum(1 for item in rows if item["headline_shape"].get(key)) / len(rows), 3)

    factor_deltas: dict[str, float] = {}
    common = set.intersection(*(set(item["factors"]) for item in approved + rejected)) if approved and rejected else set()
    for key in sorted(common):
        approved_values = [item["factors"][key] for item in approved if key in item["factors"]]
        rejected_values = [item["factors"][key] for item in rejected if key in item["factors"]]
        if approved_values and rejected_values:
            factor_deltas[key] = round(sum(approved_values) / len(approved_values) - sum(rejected_values) / len(rejected_values), 2)

    return {
        "available": bool(normalized),
        "eligible": eligible,
        "record_count": len(normalized),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "minimum_samples": max(3, int(min_samples)),
        "approved_mean_duration": mean(approved, "duration"),
        "rejected_mean_duration": mean(rejected, "duration"),
        "approved_median_duration": round(statistics.median([item["duration"] for item in approved]), 2) if approved else 0.0,
        "rejected_median_duration": round(statistics.median([item["duration"] for item in rejected]), 2) if rejected else 0.0,
        "approved_by_format": format_counts(approved),
        "rejected_by_format": format_counts(rejected),
        "approved_by_hook_family": family_counts(approved),
        "rejected_by_hook_family": family_counts(rejected),
        "headline_shape": {
            "approved_question_rate": shape_rate(approved, "question"),
            "approved_exclamation_rate": shape_rate(approved, "exclamation"),
            "approved_contrast_rate": shape_rate(approved, "contrast"),
            "approved_attention_rate": shape_rate(approved, "attention_word"),
            "approved_attribution_rate": shape_rate(approved, "attribution"),
            "approved_mean_words": round(sum(item["headline_shape"]["word_count"] for item in approved) / len(approved), 2) if approved else 0.0,
            "approved_mean_characters": round(sum(item["headline_shape"]["character_count"] for item in approved) / len(approved), 2) if approved else 0.0,
        },
        "factor_deltas": factor_deltas,
        "influence_scope": "aggregate-only; bounded prior, never a gate or fine-tune",
    }
