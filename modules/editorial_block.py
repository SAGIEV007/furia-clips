"""Editorial block dossier normalization.

The Criadores workflow exposes a useful intermediate unit between a long source
video and a final publication: a block with a thesis, context, a specific moment
and optional alternatives. This module only maps fields already present in a
Furia Clips candidate; it never invents a summary or treats a candidate as
approved content.
"""

from __future__ import annotations

from typing import Any


_ALLOWED_STATES = {"candidate", "preview", "approved", "rejected", "needs_review"}


def build_editorial_block(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a safe, explainable block dossier for a clip candidate."""
    if not isinstance(candidate, dict):
        raise ValueError("candidato editorial inválido")

    start = _non_negative(candidate.get("start", candidate.get("start_time", 0.0)), "start")
    end = _non_negative(candidate.get("end", candidate.get("end_time", start)), "end")
    if end <= start:
        raise ValueError("o bloco editorial precisa ter duração positiva")

    duration = _non_negative(candidate.get("duration", end - start), "duration")
    if duration <= 0:
        duration = end - start

    state = str(candidate.get("review_status", candidate.get("review_state", "candidate")) or "candidate")
    if state not in _ALLOWED_STATES:
        state = "candidate"

    thesis = _text(candidate.get("thesis") or candidate.get("title"))
    context_summary = _text(candidate.get("context_summary") or candidate.get("reason"))
    moment_reason = _text(candidate.get("moment_reason") or candidate.get("reason"))
    family = _text(
        candidate.get("source_family")
        or candidate.get("editorial_family")
        or candidate.get("political_editorial_type")
        or "unknown"
    )

    tags = candidate.get("tags")
    if not isinstance(tags, list):
        tags = []
    tags = [_text(tag) for tag in tags if _text(tag)][:8]

    moments = candidate.get("suggested_moments")
    if not isinstance(moments, list) or not moments:
        moments = [{
            "kind": "primary",
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
            "reason": moment_reason,
        }]
    else:
        moments = _normalize_moments(moments)

    result = {
        "state": state,
        "thesis": thesis,
        "context_summary": context_summary,
        "moment_reason": moment_reason,
        "source_family": family,
        "tags": tags,
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(duration, 3),
        "suggested_moments": moments,
        "review_required": bool(candidate.get("review_required", False)),
    }
    if candidate.get("source"):
        result["source"] = _text(candidate.get("source"))
    if candidate.get("confidence") is not None:
        result["confidence"] = _bounded_confidence(candidate.get("confidence"))
    contract = candidate.get("context_contract")
    if isinstance(contract, dict):
        result["context_contract"] = {
            "contract_version": _text(contract.get("contract_version"), 80),
            "minimum_window": contract.get("minimum_window") if isinstance(contract.get("minimum_window"), dict) else {},
            "evidence": contract.get("evidence") if isinstance(contract.get("evidence"), dict) else {},
            "completeness_score": max(0, min(100, int(contract.get("completeness_score", 0) or 0))),
            "review_required": bool(contract.get("review_required", False)),
            "review_reasons": [_text(item, 160) for item in (contract.get("review_reasons") or [])[:8]],
        }
    return result


def _normalize_moments(moments: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, moment in enumerate(moments[:8]):
        if not isinstance(moment, dict):
            continue
        try:
            start = _non_negative(moment.get("start"), "moment.start")
            end = _non_negative(moment.get("end"), "moment.end")
        except ValueError:
            continue
        if end <= start:
            continue
        normalized.append({
            "kind": _text(moment.get("kind")) or ("primary" if index == 0 else "alternative"),
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(_non_negative(moment.get("duration", end - start), "moment.duration"), 3),
            "reason": _text(moment.get("reason")),
        })
    return normalized


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())[:500]


def _non_negative(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} inválido") from exc
    if parsed < 0:
        raise ValueError(f"{field} não pode ser negativo")
    return parsed


def _bounded_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, parsed)), 4)
