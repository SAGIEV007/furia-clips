"""Bounded local editorial disagreement records.

The matrix is an audit trail, not a trainer and not a ranking input. It keeps the
automatic Furia signals, optional audiovisual evidence, optional Chub provenance,
and the human decision in separate namespaces. Records are written outside the
repository by the existing editorial session store.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "editorial-disagreement-v1"
_ALLOWED_ACTIONS = {"approved", "rejected", "needs_review"}
_ALLOWED_IDENTITY = {"validated", "unverified", "mismatch", "not_available"}
_ALLOWED_CHUB_SOURCES = {"campaign-hub", "espelho-chub-v1", ""}
_MAX_FLAGS = 24
_MAX_REASONS = 12
_MAX_TAGS = 12


def _text(value: Any, limit: int = 160) -> str:
    return str(value or "").strip()[:limit]


def _number(value: Any, *, minimum: float | None = None, maximum: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return round(result, 3)


def _list_text(value: Any, limit: int, item_limit: int = 100) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        text = _text(item, item_limit)
        if text and text not in result:
            result.append(text)
    return result[:limit]


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_flag(value: Any) -> bool | int | float | str | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return _number(value)
    if value is None:
        return None
    return _text(value, 100)


def _parse_factors(clip: dict[str, Any]) -> dict[str, Any]:
    value = clip.get("score_factors")
    if isinstance(value, str):
        import json
        try:
            value = json.loads(value or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            value = {}
    return _json_object(value)


def _automatic_signals(clip: dict[str, Any]) -> dict[str, Any]:
    factors = _parse_factors(clip)
    review_flags = factors.get("_review_flags") if isinstance(factors.get("_review_flags"), dict) else {}
    metadata = factors.get("_review_metadata") if isinstance(factors.get("_review_metadata"), dict) else {}
    flags = dict(review_flags)
    for key in (
        "context_complete",
        "payoff_complete",
        "starts_mid_sentence",
        "qa_boundary_review_required",
        "speaker_review_required",
        "technical_gate_status",
        "headline_review",
    ):
        if key in clip and key not in flags:
            flags[key] = clip.get(key)
    numeric_factors = {
        _text(key, 60): _number(value)
        for key, value in factors.items()
        if not str(key).startswith("_") and isinstance(value, (int, float))
    }
    raw_score = _number(clip.get("viral_score"), minimum=0, maximum=100) or 0
    return {
        "score": int(round(raw_score)),
        "confidence": _number(clip.get("score_confidence"), minimum=0, maximum=1),
        "score_version": _text(clip.get("editorial_score_version"), 80),
        "factors": numeric_factors,
        "flags": { _text(key, 80): _safe_flag(value) for key, value in list(flags.items())[:_MAX_FLAGS] },
        "review_required": bool(clip.get("review_required") or flags.get("review_required")),
        "review_reasons": _list_text(clip.get("review_reasons") or factors.get("review_reasons"), _MAX_REASONS, 180),
        "candidate_origin": _text(metadata.get("candidate_origin"), 40),
        "selection_source": _text(metadata.get("selection_source"), 24),
    }


def _audiovisual_evidence(clip: dict[str, Any]) -> dict[str, Any]:
    value = clip.get("multimodal_editorial_review")
    if not isinstance(value, dict):
        value = _parse_factors(clip).get("_multimodal_editorial_review")
    if not isinstance(value, dict):
        value = {}
    identity_status = _text(value.get("identity_status"), 24).lower()
    if identity_status not in _ALLOWED_IDENTITY:
        identity_status = "not_available"
    qa_evidence = []
    for item in value.get("qa_evidence", []) if isinstance(value.get("qa_evidence"), list) else []:
        if not isinstance(item, dict):
            continue
        qa_evidence.append({
            "overlap_seconds": _number(item.get("overlap_seconds"), minimum=0),
            "confidence": _number(item.get("confidence"), minimum=0, maximum=1),
            "question_present": bool(item.get("question_present")),
            "answer_present": bool(item.get("answer_present")),
            "renan_focus": bool(item.get("renan_focus")),
            "overlap_suspected": bool(item.get("overlap_suspected")),
            "reason": _text(item.get("reason"), 240),
        })
    return {
        "available": bool(value),
        "status": _text(value.get("status"), 40) or "not_available",
        "identity_status": identity_status,
        "identity_confidence": _number(value.get("identity_confidence"), minimum=0, maximum=1),
        "flags": _list_text(value.get("flags"), _MAX_FLAGS, 80),
        "qa_evidence": qa_evidence[:5],
        "message": _text(value.get("message"), 240),
    }


def _chub_context(project_context: Any) -> dict[str, Any]:
    value = project_context if isinstance(project_context, dict) else {}
    source = _text(value.get("source"), 40)
    if source not in _ALLOWED_CHUB_SOURCES:
        source = ""
    accounts = _list_text(value.get("accounts"), 4, 60)
    channel = _text(value.get("channel"), 60)
    return {
        "available": bool(value.get("available") or channel or source),
        "source": source,
        "channel": channel,
        "accounts": accounts,
        "schema_version": _text(value.get("schemaVersion"), 40),
        "fetched_at": _text(value.get("fetchedAt"), 60),
        "record_counts": {
            _text(key, 50): max(0, min(1000000, int(number or 0)))
            for key, number in list((value.get("recordCounts") or {}).items())[:12]
            if isinstance(key, str) and str(number).lstrip("-").isdigit()
        },
        "read_only": value.get("readOnly") is not False,
        "score_technical": bool(value.get("scoreTechnical", False)),
    }


def build_disagreement_record(
    clip: dict[str, Any],
    decision: dict[str, Any],
    *,
    project_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one bounded record without raw transcript, media or Chub payloads."""
    action = _text(decision.get("action"), 32).lower()
    if action not in _ALLOWED_ACTIONS:
        raise ValueError("A matriz aceita apenas decisões finais ou needs_review.")
    start = _number(clip.get("start_time"), minimum=0)
    end = _number(clip.get("end_time"), minimum=0)
    automatic = _automatic_signals(clip)
    audiovisual = _audiovisual_evidence(clip)
    human = {
        "decision": action,
        "reason_code": _text(decision.get("reason_code"), 48),
        "quality_tags": _list_text(decision.get("quality_tags"), _MAX_TAGS, 48),
        "note_present": bool(_text(decision.get("note"), 600)),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "clip": {
            "clip_id": clip.get("id"),
            "editorial_key": _text(clip.get("editorial_key"), 80),
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": _number(clip.get("duration"), minimum=0),
        },
        "automatic": automatic,
        "audiovisual": audiovisual,
        "chub": _chub_context(project_context),
        "human": human,
        "measurement": {
            "status": "descriptive_only",
            "score_used_as_decision": False,
            "causal_inference": False,
        },
    }


def summarize_records(records: list[dict[str, Any]], *, limit: int = 200) -> dict[str, Any]:
    """Return bounded descriptive counts; never compute a quality/viral score."""
    safe = [item for item in records if isinstance(item, dict) and item.get("schema_version") == SCHEMA_VERSION][-max(1, min(int(limit), 500)):]
    decisions = Counter()
    reasons = Counter()
    discordances = Counter()
    for item in safe:
        human = item.get("human") if isinstance(item.get("human"), dict) else {}
        automatic = item.get("automatic") if isinstance(item.get("automatic"), dict) else {}
        audiovisual = item.get("audiovisual") if isinstance(item.get("audiovisual"), dict) else {}
        decision = _text(human.get("decision"), 32) or "unknown"
        decisions[decision] += 1
        reason = _text(human.get("reason_code"), 48)
        if reason:
            reasons[reason] += 1
        auto_warn = bool(automatic.get("review_required") or automatic.get("flags") or audiovisual.get("flags"))
        if auto_warn and decision == "approved":
            discordances["warning_human_approved"] += 1
        elif auto_warn and decision == "rejected":
            discordances["warning_human_rejected"] += 1
        elif auto_warn:
            discordances["warning_needs_review"] += 1
        else:
            discordances["no_warning"] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "descriptive_only",
        "count": len(safe),
        "decision_counts": dict(decisions),
        "reason_counts": dict(reasons),
        "discordance_counts": dict(discordances),
        "score_used": False,
        "causal_inference": False,
    }
