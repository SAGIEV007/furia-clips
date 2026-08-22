"""Local, aggregate-only priors from reviewed short clips.

This module is calibration/observability, not model fine-tuning. It accepts
portable feature rows, strips raw text and media fields, and returns bounded
aggregates for ranking and Headline Studio. Persistent learning remains under
FuriaClipsData and never touches Campaign Hub or GitHub.
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
ALLOWED_FAMILIES = {"politico", "humor", "reacao", "bastidor", "descontraido", "conversa", "unknown"}
ALLOWED_TYPES = {"confronto", "proposta", "evidencia", "mobilizacao", "discurso", "unknown"}
ALLOWED_OPENINGS = {"question", "claim", "conflict", "casual", "other"}
ALLOWED_FAVORABILITY = {"strong", "neutral", "weak", "unknown"}
ALLOWED_REJECTION_REASONS = {"mid_sentence", "no_payoff", "not_renan_favorable", "duplicate", "low_energy", "other"}
_FORBIDDEN_TEXT = re.compile(r"(?:https?://|www\.|(?:^|[\s])(?:/home/|/tmp/|~/|[A-Za-z]:[\\/])|api[_-]?key|bearer\s+|cookie|token)", re.I)


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed if math.isfinite(parsed) else float(default)


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 100.0, default: float = 0.0) -> float:
    return max(minimum, min(maximum, _finite(value, default)))


def _label(value: Any, limit: int = 80, *, allow_forbidden: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
    if not allow_forbidden and _FORBIDDEN_TEXT.search(text):
        return ""
    return text


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _label(value, 12, allow_forbidden=True).lower()
    if text in {"true", "1", "yes", "sim", "on"}:
        return True
    if text in {"false", "0", "no", "não", "nao", "off"}:
        return False
    return default


def _canonical(value: Any, allowed: set[str], default: str = "unknown", limit: int = 64) -> str:
    normalized = _label(value, limit).lower()
    return normalized if normalized in allowed else default


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
        "question": _bool(value.get("question")),
        "exclamation": _bool(value.get("exclamation")),
        "contrast": _bool(value.get("contrast")),
        "attention_word": _bool(value.get("attention_word")),
        "attribution": _bool(value.get("attribution")),
    }


def _numeric_features(value: Any) -> dict[str, float]:
    features: dict[str, float] = {}
    sources = []
    if isinstance(value.get("factors") if isinstance(value, dict) else None, dict):
        sources.append(value["factors"])
    if isinstance(value.get("features") if isinstance(value, dict) else None, dict):
        sources.append(value["features"])
    if isinstance(value, dict):
        sources.append(value)
    for source in sources:
        for key, raw in source.items():
            if not isinstance(key, str) or len(key) > 48 or key in {"duration", "duration_sec"}:
                continue
            if isinstance(raw, (bool, int, float, str)):
                parsed = _finite(raw, float("nan"))
                if math.isfinite(parsed):
                    features[key] = round(_bounded(parsed, 0, 100), 2)
    return features


def normalize_feature_record(value: Any) -> dict[str, Any] | None:
    """Normalize one reviewed-clip row and discard raw text/media fields.

    `clip_id` is retained only as a bounded identifier for import validation;
    aggregate responses never expose the normalized rows.
    """
    if not isinstance(value, dict):
        return None
    decision = _label(value.get("label") or value.get("decision") or value.get("review_status") or value.get("action"), 24).lower()
    if decision not in ALLOWED_DECISIONS:
        return None
    duration = _finite(value.get("duration_sec", value.get("short_duration", value.get("duration", value.get("clip_duration")))), -1.0)
    if duration <= 0 or duration > 600:
        return None
    factor_source = value.get("factors") if isinstance(value.get("factors"), dict) else {}
    format_id = _canonical(value.get("format_id") or value.get("visual_format") or value.get("format") or factor_source.get("format_id"), ALLOWED_FORMATS, limit=40)
    family = _canonical(value.get("editorial_family") or value.get("family") or factor_source.get("editorial_family"), ALLOWED_FAMILIES, limit=48)
    editorial_type = _canonical(value.get("editorial_type") or value.get("type") or factor_source.get("editorial_type"), ALLOWED_TYPES, limit=48)
    opening_pattern = _canonical(value.get("opening_pattern") or factor_source.get("opening_pattern"), ALLOWED_OPENINGS, limit=24)
    favorability_note = _canonical(value.get("favorability_note") or factor_source.get("favorability_note"), ALLOWED_FAVORABILITY, limit=24)
    rejection_reason_raw = _label(value.get("rejection_reason") or factor_source.get("rejection_reason"), 40).lower()
    rejection_reason = rejection_reason_raw if rejection_reason_raw in ALLOWED_REJECTION_REASONS else ("other" if rejection_reason_raw else None)
    clip_id = _label(value.get("clip_id") or value.get("editorial_key"), 128)
    topic = _label(value.get("topic") or value.get("theme") or value.get("subject"), 80).lower() or "unknown"
    hook_family = _label(value.get("hook_family") or value.get("hook"), 60).lower() or "unknown"
    return {
        "clip_id": clip_id,
        "decision": decision,
        "duration": round(duration, 3),
        "format_id": format_id,
        "editorial_family": family,
        "editorial_type": editorial_type,
        "opening_pattern": opening_pattern,
        "has_qa_bridge": _bool(value.get("has_qa_bridge", factor_source.get("has_qa_bridge"))),
        "favorability_note": favorability_note,
        "rejection_reason": rejection_reason,
        "hook_family": _label(value.get("hook_family") or value.get("hook") or factor_source.get("hook_family"), 60).lower() or "unknown",
        "topic": topic,
        "headline_shape": _normalized_headline_shape(
            value.get("headline_shape") if isinstance(value.get("headline_shape"), dict) else value.get("headline_sanitized") or value.get("headline") or value.get("artwork_text") or ""
        ),
        "features": _numeric_features(value),
        "factors": _numeric_features(value),
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
            candidate = payload.get("records", payload.get("features", payload.get("items", [])))
            raw_records = candidate if isinstance(candidate, list) else []
    except json.JSONDecodeError:
        for line in raw_text.splitlines():
            try:
                raw_records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    try:
        cap = max(1, min(100000, int(limit)))
    except (TypeError, ValueError):
        cap = 5000
    return [record for record in (normalize_feature_record(item) for item in raw_records[:cap]) if record]


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(len(ordered) - 1, low + 1)
    weight = position - low
    return round(ordered[low] + (ordered[high] - ordered[low]) * weight, 2)


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rows:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _rates(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    total = len(rows)
    if not total:
        return {}
    counts = _counts(rows, key)
    return {name: round(count / total, 3) for name, count in sorted(counts.items())}


def _boolean_rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for item in rows if _bool(item.get(key))) / len(rows), 3) if rows else 0.0


def _shape_rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for item in rows if _bool(item.get("headline_shape", {}).get(key))) / len(rows), 3) if rows else 0.0


def build_feature_prior(records: Iterable[dict[str, Any]] | None, *, min_samples: int = 12) -> dict[str, Any]:
    """Return aggregate-only priors; no raw headline, transcript or media is retained."""
    normalized = [item for item in (normalize_feature_record(row) for row in (records or [])) if item]
    approved = [item for item in normalized if item["decision"] == "approved"]
    rejected = [item for item in normalized if item["decision"] == "rejected"]
    minimum = max(3, int(min_samples))
    eligible = len(approved) >= minimum and len(rejected) >= 3
    approved_durations = [item["duration"] for item in approved]
    rejected_durations = [item["duration"] for item in rejected]
    common = set.intersection(*(set(item["features"]) for item in approved + rejected)) if approved and rejected else set()
    factor_deltas: dict[str, float] = {}
    for key in sorted(common):
        a_values = [item["features"][key] for item in approved if key in item["features"]]
        r_values = [item["features"][key] for item in rejected if key in item["features"]]
        if a_values and r_values:
            factor_deltas[key] = round(sum(a_values) / len(a_values) - sum(r_values) / len(r_values), 2)
    format_by_family: dict[str, dict[str, int]] = {}
    for item in approved:
        family = item["editorial_family"]
        format_by_family.setdefault(family, {})[item["format_id"]] = format_by_family.setdefault(family, {}).get(item["format_id"], 0) + 1
    topic_by_format: dict[str, dict[str, int]] = {}
    for item in approved:
        topic = item["topic"]
        if topic != "unknown":
            topic_by_format.setdefault(topic, {})[item["format_id"]] = topic_by_format.setdefault(topic, {}).get(item["format_id"], 0) + 1
    topic_by_format = dict(sorted(topic_by_format.items(), key=lambda pair: -sum(pair[1].values()))[:20])
    return {
        "available": bool(normalized),
        "eligible": eligible,
        "record_count": len(normalized),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "minimum_samples": minimum,
        "approved_mean_duration": round(sum(approved_durations) / len(approved_durations), 2) if approved_durations else 0.0,
        "rejected_mean_duration": round(sum(rejected_durations) / len(rejected_durations), 2) if rejected_durations else 0.0,
        "approved_median_duration": round(statistics.median(approved_durations), 2) if approved_durations else 0.0,
        "rejected_median_duration": round(statistics.median(rejected_durations), 2) if rejected_durations else 0.0,
        "duration_median_approved": _quantile(approved_durations, 0.5),
        "duration_p25_approved": _quantile(approved_durations, 0.25),
        "duration_p75_approved": _quantile(approved_durations, 0.75),
        "approved_by_format": _counts(approved, "format_id"),
        "rejected_by_format": _counts(rejected, "format_id"),
        "overall_by_format": _counts(approved, "format_id"),
        "approved_by_hook_family": _counts(approved, "hook_family"),
        "rejected_by_hook_family": _counts(rejected, "hook_family"),
        "family_share_approved": _rates(approved, "editorial_family"),
        "opening_pattern_share_approved": _rates(approved, "opening_pattern"),
        "rejection_reason_share": _rates([item for item in rejected if item.get("rejection_reason")], "rejection_reason"),
        "format_by_family": format_by_family,
        "topic_by_format": topic_by_format,
        "has_qa_bridge_rate_approved": _boolean_rate(approved, "has_qa_bridge"),
        "headline_shape": {
            "approved_question_rate": _shape_rate(approved, "question"),
            "approved_exclamation_rate": _shape_rate(approved, "exclamation"),
            "approved_contrast_rate": _shape_rate(approved, "contrast"),
            "approved_attention_rate": _shape_rate(approved, "attention_word"),
            "approved_attribution_rate": _shape_rate(approved, "attribution"),
            "approved_mean_words": round(sum(item["headline_shape"]["word_count"] for item in approved) / len(approved), 2) if approved else 0.0,
            "approved_mean_characters": round(sum(item["headline_shape"]["character_count"] for item in approved) / len(approved), 2) if approved else 0.0,
        },
        "factor_deltas": factor_deltas,
        "headline_learning_thresholds": {
            "min_topic_format_count": 2,
            "min_overall_format_count": 4,
        },
        "influence_scope": "aggregate-only; bounded prior, never a gate or fine-tune",
    }
