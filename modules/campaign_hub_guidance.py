"""Campaign Hub -> Furia guided seed normalization.

This module turns an authorized local Campaign Hub snapshot into bounded, auditable
seeds. It does not approve clips and it never performs network access.
"""

from __future__ import annotations

from typing import Any


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number else default


def _text(value: Any, limit: int = 800) -> str:
    return " ".join(str(value or "").split())[:limit]


def _interval(value: dict[str, Any]) -> tuple[float, float] | None:
    start = next((
        _float(value.get(key))
        for key in ("start_s", "start", "start_time", "startS", "startSeconds", "fromS")
        if _float(value.get(key)) is not None
    ), None)
    end = next((
        _float(value.get(key))
        for key in ("end_s", "end", "end_time", "endS", "endSeconds", "toS")
        if _float(value.get(key)) is not None
    ), None)
    if start is None or end is None or end <= start:
        return None
    return start, end


def _map_interval(
    start: float,
    end: float,
    *,
    source_duration: float | None,
    block_start: float,
    block_end: float,
    media_duration: float | None = None,
) -> tuple[float, float, str]:
    """Map absolute Chub seconds to a downloaded block timeline when justified.

    ``media_duration`` is the length of the file actually being processed, read
    from the media itself. ``source_duration`` is only what the snapshot declares
    for the long source. The two disagree exactly in the case that matters: when
    the editor processes the downloaded block MP4, the snapshot still describes
    the whole live, so trusting the declared value leaves every seed in absolute
    seconds while the local transcript starts at zero. The real media wins; the
    declared value stays as the fallback for callers that cannot measure it.
    """
    block_span = max(0.0, block_end - block_start)
    local_duration = _float(media_duration) or _float(source_duration)
    if local_duration and block_span > 0 and abs(local_duration - block_span) <= max(15.0, block_span * 0.05):
        local_start = max(0.0, start - block_start)
        local_end = max(local_start, end - block_start)
        local_start = min(local_start, local_duration)
        local_end = min(local_end, local_duration)
        return round(local_start, 3), round(local_end, 3), "downloaded_block_timeline"
    return round(start, 3), round(end, 3), "source_timeline"


def _source_index(records: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in records.get("sources", []) or []:
        if not isinstance(item, dict):
            continue
        for key in ("id", "video_id", "videoId", "youtube_id", "youtubeId"):
            value = item.get(key)
            if value:
                index[str(value)] = item
    return index


def _belongs_to_account(item: dict[str, Any], source: dict[str, Any], account: str | None) -> bool:
    if not account:
        return True
    known = {
        str(item.get("account") or ""),
        str(item.get("account_id") or ""),
        str(source.get("account") or ""),
        str(source.get("account_id") or ""),
    }
    return not any(known) or account in known


def build_campaign_hub_guided_seeds(
    segments: list[dict[str, Any]],
    snapshot: dict[str, Any] | None,
    *,
    account: str | None = None,
    limit: int = 30,
    media_duration: float | None = None,
) -> list[dict[str, Any]]:
    """Build timestamped Chub seeds for the local transcript timeline.

    Highlights are preferred. When a block has no highlight, one block-level seed
    is emitted from its possible cut or interval so the editor can still inspect it.
    All records preserve provenance and review gates; nothing here auto-approves a
    renderable clip.

    ``media_duration`` is the measured length of the local file being processed.
    Without it the mapping can only trust the duration declared in the snapshot,
    which describes the long source and not a downloaded block.
    """
    if not isinstance(snapshot, dict):
        return []
    records = snapshot.get("records") or {}
    if not isinstance(records, dict):
        return []
    sources = _source_index(records)
    blocks = [item for item in records.get("blocks", []) or [] if isinstance(item, dict)]
    highlights = [item for item in records.get("highlights", []) or [] if isinstance(item, dict)]
    possible_cuts = [item for item in records.get("possible_cuts", []) or [] if isinstance(item, dict)]
    highlights_by_block: dict[str, list[dict[str, Any]]] = {}
    cuts_by_block: dict[str, list[dict[str, Any]]] = {}
    for item in highlights:
        highlights_by_block.setdefault(str(item.get("block_id") or item.get("blockId") or ""), []).append(item)
    for item in possible_cuts:
        cuts_by_block.setdefault(str(item.get("block_id") or item.get("blockId") or ""), []).append(item)

    seeds: list[dict[str, Any]] = []
    for block in blocks:
        block_interval = _interval(block) or (
            _float(block.get("start_s") or block.get("startS"), 0.0) or 0.0,
            _float(block.get("end_s") or block.get("endS"), 0.0) or 0.0,
        )
        block_start, block_end = block_interval
        if block_end <= block_start:
            continue
        source = sources.get(str(block.get("video_id") or block.get("videoId") or ""), {})
        if not _belongs_to_account(block, source, account):
            continue
        source_duration = _float(
            source.get("duration_s")
            or source.get("duration")
            or source.get("durationS")
            or source.get("durationSeconds")
            or block.get("source_duration")
            or block.get("sourceDuration")
            or block.get("downloaded_duration")
            or block.get("downloadedDuration")
        )
        block_key = str(block.get("id") or block.get("blockId") or "")
        highlight_rows = [(item, "highlight") for item in highlights_by_block.get(block_key, [])]
        nested_highlights = block.get("highlights") or []
        if not highlight_rows and isinstance(nested_highlights, list):
            highlight_rows = [(item, "highlight") for item in nested_highlights if isinstance(item, dict)]
        cut_rows = [(item, "possible_cut") for item in cuts_by_block.get(block_key, [])]
        nested_cuts = block.get("possibleCuts") or block.get("possible_cuts") or []
        if not cut_rows and isinstance(nested_cuts, list):
            cut_rows = [(item, "possible_cut") for item in nested_cuts if isinstance(item, dict)]
        rows = highlight_rows or cut_rows or [({}, "block")]

        for index, (row, row_kind) in enumerate(rows):
            absolute = _interval(row) or block_interval
            mapped_start, mapped_end, mapping = _map_interval(
                absolute[0], absolute[1],
                source_duration=source_duration,
                block_start=block_start,
                block_end=block_end,
                media_duration=media_duration,
            )
            if mapped_end <= mapped_start:
                continue
            is_highlight = row_kind == "highlight" or bool(row.get("highlight_id") or row.get("highlightId"))
            sentence_idx = row.get("sentence_idx") or row.get("sentenceIdx")
            seed_id = str(
                row.get("id")
                or row.get("highlight_id")
                or row.get("highlightId")
                or row.get("possible_cut_id")
                or row.get("possibleCutId")
                or (
                    f"{block.get('id') or block.get('blockId') or 'block'}-sentence-{sentence_idx}"
                    if sentence_idx is not None
                    else f"{block.get('id') or block.get('blockId') or 'block'}-seed-{index + 1}"
                )
            )
            risk_flags = list(dict.fromkeys([
                *(block.get("risk_flags") or block.get("riskFlags") or []),
                *(row.get("risk_flags") or row.get("riskFlags") or []),
            ]))
            gate_warnings = list(dict.fromkeys([
                *(block.get("gate_warnings") or block.get("gateWarnings") or []),
                *(row.get("gate_warnings") or row.get("gateWarnings") or []),
            ]))
            renan_speaking = block.get("renan_speaking")
            if renan_speaking is None:
                renan_speaking = block.get("renanSpeaking")
            speaker_gate = "pass" if renan_speaking is True else "review_required"
            seed_text = _text(row.get("text") or row.get("transcript") or block.get("summary") or block.get("title"))
            confidence = _float(row.get("confidence") or row.get("score") or block.get("confidence"))
            density_rank = _float(row.get("density_rank") or row.get("densityRank") or block.get("density_rank") or block.get("densityRank"))
            self_contained_rank = _float(row.get("self_contained_rank") or row.get("selfContainedRank") or block.get("self_contained_rank") or block.get("selfContainedRank"))
            if confidence is None:
                confidence = 0.82 if is_highlight else 0.55
            if confidence > 1:
                confidence = min(1.0, confidence / 100.0)
            seeds.append({
                "seed_id": seed_id,
                "block_id": str(block.get("id") or block.get("blockId") or ""),
                "highlight_id": str(
                    row.get("id")
                    or row.get("highlight_id")
                    or row.get("highlightId")
                    or (f"sentence-{sentence_idx}" if sentence_idx is not None else "")
                ) if is_highlight else "",
                "video_id": str(block.get("video_id") or block.get("videoId") or source.get("id") or ""),
                "source_ref": str(source.get("youtube_id") or source.get("youtubeId") or source.get("video_id") or source.get("videoId") or source.get("url") or source.get("id") or ""),
                "absolute_start": round(absolute[0], 3),
                "absolute_end": round(absolute[1], 3),
                "start": mapped_start,
                "end": mapped_end,
                "duration": round(mapped_end - mapped_start, 3),
                "timeline_mapping": mapping,
                "seed_text": seed_text,
                "title": _text(row.get("title") or block.get("title"), 240),
                "summary": _text(row.get("summary") or block.get("summary"), 500),
                "trigger_question": _text(
                    row.get("trigger_question")
                    or row.get("triggerQuestion")
                    or block.get("trigger_question")
                    or block.get("triggerQuestion"),
                    400,
                ),
                "topics": list(block.get("topics") or row.get("topics") or [])[:20],
                "category": _text(row.get("category") or block.get("category"), 160),
                "renan_speaking": renan_speaking,
                "speaker_gate": speaker_gate,
                "needs_context": bool(
                    block.get("needs_context")
                    or block.get("needsContext")
                    or row.get("needs_context")
                    or row.get("needsContext")
                    or block.get("trigger_question")
                    or block.get("triggerQuestion")
                ),
                "risk_flags": risk_flags[:20],
                "gate_warnings": gate_warnings[:20],
                "trust_tier": str(
                    row.get("trust_tier")
                    or row.get("trustTier")
                    or block.get("trust_tier")
                    or block.get("trustTier")
                    or "third_party"
                ),
                "confidence": round(max(0.0, min(1.0, confidence)), 3),
                "density_rank": round(max(0.0, min(100.0, density_rank)), 3) if density_rank is not None else None,
                "self_contained_rank": round(max(0.0, min(100.0, self_contained_rank)), 3) if self_contained_rank is not None else None,
                "self_contained_reason": _text(row.get("self_contained_reason") or row.get("selfContainedReason") or block.get("self_contained_reason") or block.get("selfContainedReason"), 500),
                "possible_cuts": int(_float(row.get("possible_cuts") or row.get("possibleCuts") or block.get("possible_cuts") or block.get("possibleCuts"), 0) or 0),
                "content_class": str(row.get("content_class") or row.get("contentClass") or block.get("content_class") or block.get("contentClass") or ""),
                "labeler_version": str(block.get("labeler_version") or block.get("labelerVersion") or ""),
                "prompt_version": str(block.get("prompt_version") or block.get("promptVersion") or ""),
                "source_kind": "highlight" if is_highlight else "block_seed",
                "provenance": {
                    "snapshot_version": str(snapshot.get("version") or ""),
                    "account": account or str(snapshot.get("default_account") or ""),
                    "block_id": str(block.get("id") or block.get("blockId") or ""),
                    "highlight_id": str(
                        row.get("id")
                        or row.get("highlight_id")
                        or row.get("highlightId")
                        or (f"sentence-{sentence_idx}" if sentence_idx is not None else "")
                    ) if is_highlight else "",
                    "sentence_idx": sentence_idx,
                    "source_ref": str(
                        source.get("youtube_id")
                        or source.get("youtubeId")
                        or source.get("video_id")
                        or source.get("videoId")
                        or source.get("url")
                        or source.get("id")
                        or block.get("video_id")
                        or block.get("videoId")
                        or ""
                    ),
                },
            })

    seeds.sort(key=lambda item: (
        0 if item.get("source_kind") == "highlight" else 1,
        0 if item.get("renan_speaking") is True else 1,
        -float(item.get("confidence") or 0.0),
        float(item.get("start") or 0.0),
    ))
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[float, float, str]] = set()
    for seed in seeds:
        key = (round(float(seed["start"]), 3), round(float(seed["end"]), 3), str(seed.get("seed_text") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(seed)
        if len(deduplicated) >= max(1, min(250, int(limit or 100))):
            break
    return deduplicated
