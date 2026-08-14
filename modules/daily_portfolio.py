"""Global daily portfolio selection for a multi-live editorial workflow.

The selector is intentionally conservative: 39–50 is an operating target, not a
quota. Candidates below quality gates are excluded even when that produces fewer
than 39 clips. The input is expected to contain clips already scored by
``EditorialRanker``; the selector only performs global competition, deduplication,
and source/family diversification.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable


DEFAULT_MIN_SCORE = 62
DEFAULT_MAX_CLIPS = 50
DEFAULT_TARGET_MIN = 39
DEFAULT_MAX_PER_SOURCE = 8
DEFAULT_MAX_PER_FAMILY = 14
PREFERRED_MAX_DURATION = 180.0


def _source_key(clip: dict) -> str:
    for key in ("source_id", "live_id", "source", "origin", "video_id"):
        value = str(clip.get(key) or "").strip()
        if value:
            return value
    return "unknown_source"


def _family_key(clip: dict) -> str:
    signals = clip.get("political_signals") or {}
    return str(
        clip.get("editorial_family")
        or signals.get("editorial_family")
        or clip.get("political_editorial_type")
        or "conversa"
    )


def _format_key(clip: dict) -> str:
    return str(clip.get("visual_format") or clip.get("format_family") or "desconhecido")


def _text_key(clip: dict) -> str:
    text = " ".join(str(clip.get("text") or "").lower().split())
    return text


def _quality_reasons(clip: dict, min_score: float) -> list[str]:
    reasons: list[str] = []
    score = float(clip.get("editorial_potential_score", clip.get("viral_score", 0)) or 0)
    if score < min_score:
        reasons.append("score_abaixo_do_minimo")
    if clip.get("passes_gates") is False:
        reasons.append("gate_explicitamente_reprovado")

    factors = clip.get("factors") or {}
    political = clip.get("political_signals") or {}
    context = factors.get("context_completeness", political.get("context_completeness"))
    completeness = factors.get("completeness", political.get("conclusion"))
    clarity = factors.get("clarity")
    if context is not None and float(context) < 55:
        reasons.append("contexto_insuficiente")
    if completeness is not None and float(completeness) < 55:
        reasons.append("conclusao_ou_payoff_insuficiente")
    if clarity is not None and float(clarity) < 42:
        reasons.append("fala_pouco_clara")
    if not _text_key(clip):
        reasons.append("sem_transcricao")
    return reasons


def _similarity(left: str, right: str) -> float:
    left_words = set(left.split())
    right_words = set(right.split())
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def build_daily_portfolio(
    candidates: Iterable[dict],
    *,
    target_min: int = DEFAULT_TARGET_MIN,
    max_clips: int = DEFAULT_MAX_CLIPS,
    min_score: float = DEFAULT_MIN_SCORE,
    max_per_source: int = DEFAULT_MAX_PER_SOURCE,
    max_per_family: int = DEFAULT_MAX_PER_FAMILY,
    duplicate_similarity: float = 0.86,
) -> dict:
    """Return a globally ranked, quality-gated daily portfolio and audit data."""
    source_candidates = [dict(candidate) for candidate in candidates]
    source_candidates.sort(
        key=lambda clip: (
            float(clip.get("editorial_potential_score", clip.get("viral_score", 0)) or 0),
            float((clip.get("factors") or {}).get("duration_fit", clip.get("duration_fit", 50)) or 50),
            float(clip.get("confidence", 0) or 0),
            -float(clip.get("duration", 0) or 0),
        ),
        reverse=True,
    )

    rejected = Counter()
    eligible: list[dict] = []
    seen_texts: list[str] = []
    for clip in source_candidates:
        reasons = _quality_reasons(clip, min_score)
        if reasons:
            for reason in reasons:
                rejected[reason] += 1
            continue
        text_key = _text_key(clip)
        if any(_similarity(text_key, existing) >= duplicate_similarity for existing in seen_texts):
            rejected["duplicata_semantica"] += 1
            continue
        seen_texts.append(text_key)
        eligible.append(clip)

    selected: list[dict] = []
    source_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    format_counts: Counter[str] = Counter()
    deferred_by_family: list[dict] = []

    # First pass uses a round-robin over sources. This avoids letting one live
    # consume the portfolio before other lives have been represented.
    remaining = list(eligible)
    while remaining and len(selected) < max_clips:
        progress = False
        for candidate in list(remaining):
            if len(selected) >= max_clips:
                break
            source = _source_key(candidate)
            family = _family_key(candidate)
            if source_counts[source] >= max_per_source:
                continue
            if family_counts[family] >= max_per_family:
                deferred_by_family.append(candidate)
                remaining.remove(candidate)
                continue
            selected.append(candidate)
            source_counts[source] += 1
            family_counts[family] += 1
            format_counts[_format_key(candidate)] += 1
            remaining.remove(candidate)
            progress = True
        if not progress:
            break

    # If a family cap prevented filling the requested range, relax only that
    # soft cap; source concentration remains bounded and quality gates remain.
    if len(selected) < min(target_min, max_clips) and deferred_by_family:
        for candidate in deferred_by_family:
            if len(selected) >= max_clips:
                break
            source = _source_key(candidate)
            if source_counts[source] >= max_per_source:
                rejected["limite_por_live"] += 1
                continue
            selected.append(candidate)
            source_counts[source] += 1
            family_counts[_family_key(candidate)] += 1
            format_counts[_format_key(candidate)] += 1

    selected.sort(
        key=lambda clip: (
            float(clip.get("editorial_potential_score", clip.get("viral_score", 0)) or 0),
            float((clip.get("factors") or {}).get("duration_fit", clip.get("duration_fit", 50)) or 50),
            float(clip.get("confidence", 0) or 0),
            -float(clip.get("duration", 0) or 0),
        ),
        reverse=True,
    )
    for index, clip in enumerate(selected, start=1):
        clip["daily_portfolio_rank"] = index
        clip["daily_portfolio_source"] = _source_key(clip)
        clip["daily_portfolio_family"] = _family_key(clip)
        clip["daily_portfolio_format"] = _format_key(clip)

    if len(eligible) > len(selected):
        rejected["limite_do_portfolio"] += len(eligible) - len(selected)

    return {
        "clips": selected,
        "summary": {
            "candidate_count": len(source_candidates),
            "eligible_count": len(eligible),
            "selected_count": len(selected),
            "target_min": target_min,
            "target_max": max_clips,
            "target_met": target_min <= len(selected) <= max_clips,
            "quality_floor": min_score,
            "preferred_max_duration": PREFERRED_MAX_DURATION,
            "duration_policy": "shorter_when_context_complete; contextual_exceptions_allowed",
            "source_counts": dict(source_counts),
            "family_counts": dict(family_counts),
            "format_counts": dict(format_counts),
            "rejections": dict(rejected),
            "status": "faixa_operacional_atingida" if target_min <= len(selected) <= max_clips else "material_insuficiente_ou_concentrado",
        },
    }
