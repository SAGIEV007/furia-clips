"""What Furia understood about a source, before a single clip is rendered.

Until now this reading existed only inside the run. Turns were detected, subjects
were segmented, blocks were matched — and none of it reached the operator, who
received a folder of files and had to open a JSON to find out what the program
had thought. The editor said it plainly: the program cuts and never shows what it
understood.

The reading has two possible origins and they are not equivalent, so the origin
is always reported alongside it. When the Acervo already published blocks for the
source, those are the reading: a person reviewed the boundaries, wrote the title
and marked the strong moments. When it has not, Furia reads the source itself
from the transcript — the seams of the conversation and the subjects that recur —
and what it produces is an honest approximation, not a title anybody wrote.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .interview_turns import detect_interviewer_turns, looks_like_an_interview
from .topic_segmenter import segment_transcript


# Below this a stretch is not a block, it is a fragment: the Acervo's own blocks
# have a median duration of 87 seconds and its shortest are around half a minute.
MIN_UNIT_DURATION_S = 25.0


def _acervo_units(snapshot_path: str | Path) -> list[dict[str, Any]]:
    """The blocks a person reviewed, in the shape the panel renders."""
    try:
        payload = json.loads(Path(str(snapshot_path)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, dict):
        return []

    highlights_by_block: dict[str, list[dict[str, Any]]] = {}
    for highlight in records.get("highlights") or []:
        if not isinstance(highlight, dict):
            continue
        highlights_by_block.setdefault(str(highlight.get("block_id") or ""), []).append({
            "start_s": highlight.get("start_s"),
            "end_s": highlight.get("end_s"),
            "text": _shorten(highlight.get("text"), 200),
            "reason": _shorten(highlight.get("reason"), 200),
        })

    units = []
    for block in records.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        start = _number(block.get("start_s"))
        end = _number(block.get("end_s"))
        if start is None or end is None or end <= start:
            continue
        units.append({
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "duration_s": round(end - start, 2),
            "title": str(block.get("title") or "").strip(),
            "summary": str(block.get("summary") or "").strip(),
            "question": str(block.get("trigger_question") or "").strip(),
            "subject_terms": [str(topic) for topic in (block.get("topics") or [])][:6],
            "highlights": sorted(
                highlights_by_block.get(str(block.get("id") or ""), []),
                key=lambda item: _number(item.get("start_s")) or 0.0,
            ),
            "renan_speaking": block.get("renan_speaking"),
            "density_rank": block.get("density_rank"),
            "possible_cuts": block.get("possible_cuts"),
            "needs_context": block.get("needs_context"),
            "risk_flags": block.get("risk_flags") or [],
            "provenance": "acervo",
        })
    units.sort(key=lambda unit: unit["start_s"])
    return units


def _interview_units(segments: list[dict[str, Any]], duration_s: float) -> list[dict[str, Any]]:
    """Question-and-answer stretches, cut where the subject changes.

    Only turns that change the subject open a unit. A follow-up presses the same
    point and belongs inside the answer it follows; treating it as a boundary
    chops one exchange into pieces that read as unfinished.
    """
    turns = detect_interviewer_turns(segments)
    if not looks_like_an_interview(turns, duration_s):
        return []
    openings = [turn for turn in turns if turn["major"]] or turns
    if len(openings) < 2:
        return []

    bounds = [turn["start_s"] for turn in openings] + [duration_s]
    units = []
    for index, turn in enumerate(openings):
        start, end = bounds[index], bounds[index + 1]
        if end - start < MIN_UNIT_DURATION_S:
            continue
        answer = [
            item for item in segments
            if turn["end_s"] <= (_number(item.get("start")) or 0.0) < end
        ]
        units.append({
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "duration_s": round(end - start, 2),
            "title": "",
            "summary": "",
            "question": _shorten(turn.get("text"), 200),
            "subject_terms": _terms_between(segments, start, end),
            "highlights": [],
            "renan_speaking": None,
            "answer_segments": len(answer),
            "provenance": "furia_interview_turns",
        })
    return units


def _topic_units(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Subjects that hold together, for sources that are not a conversation."""
    units = []
    for unit in segment_transcript(segments) or []:
        start, end = _number(unit.get("start_s")), _number(unit.get("end_s"))
        if start is None or end is None or end - start < MIN_UNIT_DURATION_S:
            continue
        units.append({
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "duration_s": round(end - start, 2),
            "title": "",
            "summary": "",
            "question": "",
            "subject_terms": [str(term) for term in (unit.get("topic_terms") or [])][:6],
            "highlights": [],
            "renan_speaking": None,
            "carries_subject": unit.get("carries_subject"),
            "provenance": "furia_topic_segmenter",
        })
    return units


def read_source(
    segments: list[dict[str, Any]] | None = None,
    *,
    snapshot_path: str | Path | None = None,
    duration_s: float | None = None,
) -> dict[str, Any]:
    """The reading to show the operator, and where it came from.

    Reviewed blocks always win. They carry a title somebody wrote and boundaries
    somebody checked, and no heuristic over a transcript competes with that.
    """
    segments = [
        item for item in segments or []
        if str(item.get("text") or "").strip() and _number(item.get("end")) is not None
    ]
    span = float(duration_s or 0.0) or max(
        (_number(item.get("end")) or 0.0 for item in segments), default=0.0
    )

    if snapshot_path:
        units = _acervo_units(snapshot_path)
        if units:
            return _summarise(units, "acervo", span)

    if segments:
        units = _interview_units(segments, span)
        if units:
            return _summarise(units, "furia_entrevista", span)
        units = _topic_units(segments)
        if units:
            return _summarise(units, "furia_temas", span)

    return {
        "origin": "nenhuma",
        "units": [],
        "unit_count": 0,
        "covered_s": 0.0,
        "coverage_ratio": 0.0,
        "duration_s": round(span, 2),
        "reviewed": False,
    }


def _summarise(units: list[dict[str, Any]], origin: str, span: float) -> dict[str, Any]:
    covered = sum(unit["duration_s"] for unit in units)
    return {
        "origin": origin,
        "units": units,
        "unit_count": len(units),
        "covered_s": round(covered, 2),
        "coverage_ratio": round(covered / span, 3) if span > 0 else 0.0,
        "duration_s": round(span, 2),
        # Whether a person checked these boundaries. The panel says so out loud,
        # because it changes how much the operator should trust them.
        "reviewed": origin == "acervo",
        "highlight_count": sum(len(unit.get("highlights") or []) for unit in units),
    }


def _terms_between(segments, start, end) -> list[str]:
    """The words this stretch keeps returning to.

    These are frequent terms, not a title: presenting them as one would be a
    small lie that compounds, because the operator would trust a summary Furia
    never wrote.
    """
    window = [
        item for item in segments
        if (_number(item.get("start")) or 0.0) >= start and (_number(item.get("end")) or 0.0) <= end
    ]
    if not window:
        return []
    units = segment_transcript(window, min_sentences=4)
    if units:
        return [str(term) for term in (units[0].get("topic_terms") or [])][:6]
    return []


def _shorten(text, limit: int) -> str:
    """Cut long text at a word, not in the middle of one.

    A question that ends "...serão entrevistados ao" reads as a bug in the
    program rather than as an abbreviation.
    """
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].rstrip(",;:—- ")
    return f"{clipped}…"


def _number(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
