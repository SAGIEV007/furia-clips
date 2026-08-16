"""Conservative source-boundary detection for promo/intro versus live content.

The detector is intentionally narrow: it only proposes a boundary when an explicit
live-opening greeting appears after a meaningful pre-roll. It never rewrites source
timestamps and it never deletes the archived full transcript; callers decide whether
to use the proposed boundary for editorial selection.
"""

from __future__ import annotations

import re
from typing import Any


_LIVE_OPENING_PATTERNS = (
    r"\bsenhoras\s+e\s+senhores\b",
    r"\bsejam\s+bem[-\s]?vindos\b",
    r"\bbem[-\s]?vindos\s+(?:ao|a|à)\b",
    r"\bboa\s+noite\b",
    r"\bbom\s+dia\b",
    r"\bboa\s+tarde\b",
)
_LIVE_STRONG_CUES = re.compile(r"\b(sejam\s+bem[-\s]?vindos|live|programa|hist[oó]ria|epis[oó]dio|da\s+hist[oó]ria)\b", re.IGNORECASE)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _opening_evidence(text: str) -> list[str]:
    normalized = _text(text)
    return [pattern for pattern in _LIVE_OPENING_PATTERNS if re.search(pattern, normalized)]


def detect_live_content_start(
    transcription: dict | None,
    *,
    duration_seconds: float | None = None,
    manual_start_seconds: float | None = None,
) -> dict:
    """Return a conservative proposed live-content start.

    A greeting at the beginning of a normal live is not a boundary. The automatic
    detector requires the greeting to occur after 45 seconds and before the first
    20 percent/10-minute observation window. A manual value is accepted only when
    it is finite, non-negative and inside the source duration.
    """
    try:
        duration = max(0.0, float(duration_seconds or 0.0))
    except (TypeError, ValueError):
        duration = 0.0

    if manual_start_seconds is not None:
        try:
            manual = float(manual_start_seconds)
        except (TypeError, ValueError):
            manual = -1.0
        if manual >= 0 and (duration <= 0 or manual < duration):
            return {
                "status": "manual",
                "content_start_seconds": round(manual, 3),
                "confidence": 1.0,
                "evidence": ["manual_start_seconds"],
                "reason": "fronteira fornecida pelo operador",
            }

    segments = transcription.get("segments", []) if isinstance(transcription, dict) else []
    candidates = []
    observation_end = min(600.0, duration * 0.20) if duration > 0 else 600.0
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        try:
            start = float(segment.get("start", 0) or 0)
        except (TypeError, ValueError):
            continue
        if start < 45.0 or start > observation_end:
            continue
        text = str(segment.get("text", "") or "").strip()
        evidence = _opening_evidence(text)
        if evidence:
            strong_cues = _LIVE_STRONG_CUES.findall(text)
            try:
                end = float(segment.get("end", start) or start)
            except (TypeError, ValueError):
                end = start
            candidates.append({
                "start": start,
                "end": end,
                "evidence": evidence,
                "strong_cues": strong_cues,
                "text": text,
            })

    if not candidates:
        return {
            "status": "not_detected",
            "content_start_seconds": 0.0,
            "confidence": 0.0,
            "evidence": [],
            "reason": "nenhuma saudação explícita de início após pré-roll significativo",
        }

    selected = candidates[0]
    # Promotional narration often says only “senhoras e senhores, boa noite”.
    # If a stronger live/program cue appears shortly afterward, prefer the best
    # later cue, but do not keep moving the boundary to every later greeting.
    def candidate_strength(candidate: dict) -> tuple[int, int, float]:
        return (
            len(candidate["strong_cues"]) * 3 + len(candidate["evidence"]),
            len(candidate["strong_cues"]),
            -candidate["start"],
        )

    for candidate in candidates[1:]:
        close_to_previous = candidate["start"] - selected["start"] <= 90.0
        if close_to_previous and candidate["strong_cues"] and candidate_strength(candidate) > candidate_strength(selected):
            selected = candidate
    if not selected["strong_cues"]:
        return {
            "status": "not_detected",
            "content_start_seconds": 0.0,
            "confidence": 0.0,
            "evidence": selected["evidence"],
            "excerpt": selected["text"][:240],
            "reason": "saudação genérica isolada não confirma fronteira de pré-roll",
        }

    start = selected["start"]
    evidence = selected["evidence"]
    confidence = 0.90 if len(evidence) >= 2 else 0.86
    return {
        "status": "detected",
        "content_start_seconds": round(start, 3),
        "confidence": confidence,
        "evidence": evidence,
        "strong_cues": selected["strong_cues"],
        "excerpt": selected["text"][:240],
        "reason": "saudação forte de início de live preferida após pré-roll ambíguo" if selected is not candidates[0] else "saudação explícita de início após pré-roll significativo",
    }


def trim_transcription_to_live_start(transcription: dict | None, boundary: dict | None) -> dict:
    """Create a selection transcript while preserving canonical source timestamps."""
    source = dict(transcription or {})
    try:
        start = max(0.0, float((boundary or {}).get("content_start_seconds", 0.0) or 0.0))
    except (TypeError, ValueError):
        start = 0.0
    if start <= 0:
        return {**source, "source_boundary": boundary or {"status": "not_detected", "content_start_seconds": 0.0}}

    segments = []
    for segment in source.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        try:
            end = float(segment.get("end", 0) or 0)
        except (TypeError, ValueError):
            continue
        if end > start:
            segments.append(dict(segment))
    full_text = " ".join(str(segment.get("text", "") or "").strip() for segment in segments).strip()
    return {
        **source,
        "segments": segments,
        "full_text": full_text,
        "segment_count": len(segments),
        "source_boundary": boundary or {},
        "selection_scope": "live_content_only",
    }
