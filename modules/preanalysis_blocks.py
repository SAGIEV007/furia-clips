"""Where the pre-analysis blocks come from, in order of how much they are worth.

The panel that lists blocks read from exactly one place: a global Campaign Hub
snapshot whose path was a settings field somebody had to fill by hand. In
practice nobody ever filled it, so the panel said "Memória não carregada" on
every video ever loaded, and the editor reasonably concluded the feature did
nothing.

Meanwhile two other readings of the same source already existed and were being
thrown away. The Acervo export filed per video by :mod:`acervo_library` carries
blocks a person reviewed. And when there is no export at all — the common case,
since most sources the editor cuts were never labelled — Furia's own reading of
the transcript still finds the seams of the conversation.

So the rule here is a fall-through, and the origin travels with the answer:

1. the Acervo export for this exact video, when it is on disk;
2. the global Campaign Hub snapshot, filtered to this video, for whoever has one;
3. Furia's reading of the loaded transcript.

Only the first was reviewed by a person, and the panel says so out loud. A
derived block is deliberately given no title: a title is something somebody
wrote, and promoting frequent terms to one would be a small lie the operator
would then trust. What it gets instead is its position in the source and the
opening of what is actually said inside it, verbatim — which is information the
transcript really contains.
"""

from __future__ import annotations

from typing import Any

from .acervo_library import find_snapshot_for, youtube_id_from_name
from .editorial_block_memory import list_blocks
from .source_reading import read_source


# What the card shows before the operator opens anything. Long enough to tell two
# stretches about the same subject apart, short enough not to become a wall.
_SUMMARY_CHARS = 240


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _verbatim_opening(segments: list[dict[str, Any]], start: float, end: float) -> str:
    """The first thing actually said inside the stretch, in the speaker's words.

    Not a summary. Furia did not write it and does not claim to have understood
    it; it is the transcript, cut at a word boundary.
    """
    spoken: list[str] = []
    for item in sorted(segments or [], key=lambda entry: _number(entry.get("start"))):
        at = _number(item.get("start"))
        if at < start:
            continue
        if at >= end:
            break
        text = " ".join(str(item.get("text") or "").split())
        if not text:
            continue
        spoken.append(text)
        if len(" ".join(spoken)) >= _SUMMARY_CHARS:
            break
    joined = " ".join(spoken)
    if len(joined) <= _SUMMARY_CHARS:
        return joined
    return joined[:_SUMMARY_CHARS].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…"


def _derived_cards(
    reading: dict[str, Any],
    segments: list[dict[str, Any]],
    video_id: str,
    query: str,
) -> list[dict[str, Any]]:
    """Turn Furia's own reading into the shape the block panel renders."""
    cards: list[dict[str, Any]] = []
    needle = query.lower().strip()
    for index, unit in enumerate(reading.get("units") or [], start=1):
        start, end = _number(unit.get("start_s")), _number(unit.get("end_s"))
        # The question already has its own line on the card; quoting it again as
        # the opening of the block just showed the same sentence twice.
        summary = _verbatim_opening(segments, _number(unit.get("answer_start_s"), start), end)
        if needle and needle not in f"{summary} {unit.get('question') or ''} {' '.join(unit.get('subject_terms') or [])}".lower():
            continue
        cards.append({
            "id": f"local:{index}:{int(start)}",
            # No title: nobody wrote one. The position is a fact, a title is not.
            "title": "",
            "label": f"Trecho {index}",
            "summary": summary,
            "summary_is_verbatim": True,
            "category": "",
            "topics": [str(term) for term in (unit.get("subject_terms") or [])][:6],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(max(0.0, end - start), 3),
            "video_id": video_id,
            "source": {"title": "leitura local desta fonte"},
            "trigger_question": str(unit.get("question") or ""),
            "renan_speaking": unit.get("renan_speaking"),
            "self_contained_rank": None,
            "density_rank": None,
            "needs_context": False,
            "possible_cuts": None,
            "risk_flags": [],
            "gate_warnings": [],
            "trust_tier": "leitura do Furia",
            "highlight_count": 0,
            "highlights": [],
            "provenance": unit.get("provenance") or "furia",
            "download_mode": "local_interval_when_source_available",
        })
    return cards


def blocks_for_source(
    *,
    video_path: str | None = None,
    source_url: str | None = None,
    segments: list[dict[str, Any]] | None = None,
    duration_s: float | None = None,
    snapshot_path: str | None = None,
    query: str = "",
    prioritize_renan: bool = False,
    limit: int = 80,
) -> dict[str, Any]:
    """List the blocks worth looking at for this source, saying where they came from."""
    from .acervo_library import youtube_id_from_url
    
    video_id = ""
    if source_url:
        video_id = youtube_id_from_url(source_url) or ""
    if not video_id:
        video_id = youtube_id_from_name(str(video_path or "")) or ""

    export = find_snapshot_for(video_path) if video_path else None
    if export:
        payload = list_blocks(str(export), query=query, prioritize_renan=prioritize_renan, limit=limit)
        if payload.get("blocks"):
            return {**payload, "origin": "acervo", "reviewed": True, "video_id": video_id}

    if snapshot_path:
        payload = list_blocks(
            snapshot_path,
            query=query,
            prioritize_renan=prioritize_renan,
            source_ref=video_id or None,
            limit=limit,
        )
        if payload.get("blocks"):
            return {**payload, "origin": "campaign_hub", "reviewed": True, "video_id": video_id}

    segments = [item for item in segments or [] if str(item.get("text") or "").strip()]
    if segments:
        reading = read_source(segments, duration_s=duration_s)
        cards = _derived_cards(reading, segments, video_id, query)
        if cards:
            return {
                "available": True,
                "status": "ready",
                "origin": reading.get("origin") or "furia",
                "reviewed": False,
                "video_id": video_id,
                "total": len(cards),
                "offset": 0,
                "limit": limit,
                "coverage_ratio": reading.get("coverage_ratio", 0.0),
                "duration_s": reading.get("duration_s", 0.0),
                "blocks": cards[:max(1, int(limit or 80))],
            }
        return {
            "available": False,
            "origin": "nenhuma",
            "reviewed": False,
            "blocks": [],
            "total": 0,
            "message": (
                "A transcrição carregada não rende trechos longos o bastante para virar bloco. "
                "Confira se ela cobre o vídeo inteiro."
            ),
        }

    return {
        "available": False,
        "origin": "nenhuma",
        "reviewed": False,
        "blocks": [],
        "total": 0,
        "message": (
            "Carregue o vídeo e a transcrição para o Furia ler a fonte, "
            "ou importe os blocos do Acervo deste vídeo."
        ),
    }
