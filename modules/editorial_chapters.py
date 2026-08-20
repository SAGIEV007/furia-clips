"""Deterministic temporal chapters for context-safe clip selection.

The chapter map is deliberately conservative: it groups adjacent transcript
segments into coherent editorial blocks, keeps question–answer spans together,
and exposes enough metadata for the ranker and review UI to explain why a clip
crosses (or does not cross) a chapter boundary.
"""

from __future__ import annotations

import re
from collections import Counter


_DEFAULT_TARGET_SECONDS = 85.0
_MAX_CHAPTER_SECONDS = 180.0
_HARD_GAP_SECONDS = 8.0


def build_editorial_chapters(
    segments: list[dict],
    qa_candidates: list[dict] | None = None,
    *,
    target_seconds: float = _DEFAULT_TARGET_SECONDS,
    max_chapters: int = 120,
) -> list[dict]:
    """Build contiguous editorial chapters from enriched transcript segments.

    A chapter boundary is allowed at a meaningful pause, after a completed
    question–answer bridge, or near the target duration. Long spans are split
    only at a segment boundary and never in the middle of a detected QA bridge.
    """
    normalized = _normalize_segments(segments)
    if not normalized:
        return []

    bridges = _bridge_ranges(qa_candidates or [])
    groups: list[list[dict]] = []
    current: list[dict] = []

    for index, segment in enumerate(normalized):
        current.append(segment)
        next_segment = normalized[index + 1] if index + 1 < len(normalized) else None
        if next_segment is None:
            # O grupo corrente fecha aqui, e só aqui: sem esvaziá-lo, o `if
            # current` logo abaixo fechava o mesmo grupo uma segunda vez e todo
            # vídeo terminava com o último capítulo duplicado.
            groups.append(current)
            current = []
            break

        start = float(current[0]["start"])
        end = float(segment["end"])
        duration = end - start
        gap = max(0.0, float(next_segment["start"]) - end)
        bridge_active = _inside_bridge(end, bridges) or _inside_bridge(float(next_segment["start"]), bridges)
        sentence_finished = bool(re.search(r"[.!?]$", str(segment.get("text", "")).strip()))
        speaker_changed = bool(segment.get("speaker")) and bool(next_segment.get("speaker")) and segment.get("speaker") != next_segment.get("speaker")

        hard_boundary = gap >= _HARD_GAP_SECONDS
        natural_boundary = (
            duration >= target_seconds
            and (sentence_finished or gap >= 1.0 or speaker_changed)
        )
        forced_boundary = duration >= _MAX_CHAPTER_SECONDS
        if not bridge_active and (hard_boundary or natural_boundary or forced_boundary):
            groups.append(current)
            current = []

    if current:
        groups.append(current)

    chapters = []
    for chapter_index, group in enumerate(groups[:max_chapters], start=1):
        chapter_start = float(group[0]["start"])
        chapter_end = float(group[-1]["end"])
        text = " ".join(str(item.get("text", "")).strip() for item in group).strip()
        qa_ids = [
            index for index, bridge in enumerate(bridges)
            if _interval_overlap(chapter_start, chapter_end, bridge[0], bridge[1]) > 0
        ]
        topic_terms = _topic_terms(text)
        chapters.append({
            "id": f"chapter-{chapter_index:03d}",
            "index": chapter_index - 1,
            "start": round(chapter_start, 3),
            "end": round(chapter_end, 3),
            "duration": round(max(0.0, chapter_end - chapter_start), 3),
            "segment_start": int(group[0].get("segment_index", 0)),
            "segment_end": int(group[-1].get("segment_index", 0)),
            "segment_count": len(group),
            "has_question": any(bool(item.get("is_question")) for item in group),
            "has_qa_bridge": bool(qa_ids),
            "qa_candidate_ids": qa_ids,
            "topic_terms": topic_terms,
            "label": " / ".join(topic_terms[:3]) or "bloco editorial",
            "boundary_policy": "preserve_qa_bridge" if qa_ids else "natural_pause",
        })
    return chapters


def annotate_clip_with_chapters(clip: dict, editorial_context: dict | None) -> dict:
    """Attach chapter evidence to a clip without changing its timestamps."""
    result = dict(clip or {})
    context = editorial_context or {}
    chapters = context.get("editorial_chapters", [])
    hook_candidates = context.get("hook_candidates", [])
    local_bridge = bool(result.get("qa_bridge_local"))
    local_basis = str(result.get("qa_boundary_basis_local") or "turnos_do_entrevistador")

    if not chapters:
        result.setdefault("editorial_chapter_available", False)
        result.setdefault("chapter_coherence_score", None)
        result.setdefault("editorial_chapter_ids", [])
        result.setdefault("chapter_count", 0)
        result.setdefault("qa_bridge", local_bridge)
        result.setdefault("qa_boundary_basis", local_basis if local_bridge else None)
        result.setdefault("qa_boundary_review_required", False)
        _attach_nearest_hook(result, hook_candidates)
        return result

    start = float(result.get("start", 0) or 0)
    end = float(result.get("end", start) or start)
    if end <= start:
        end = start + float(result.get("duration", 0) or 0)

    overlaps = []
    for chapter in chapters:
        overlap = _interval_overlap(start, end, float(chapter.get("start", 0)), float(chapter.get("end", 0)))
        if overlap > 0:
            overlaps.append((chapter, overlap))

    ids = [chapter["id"] for chapter, _ in overlaps]
    qa_bridge = False
    qa_boundary_basis = None
    qa_boundary_review_required = False
    for candidate in (editorial_context or {}).get("qa_candidates", []):
        qa_start = float(candidate.get("start", 0) or 0)
        qa_end = float(candidate.get("end", qa_start) or qa_start)
        if _interval_overlap(start, end, qa_start, qa_end) <= 0:
            continue
        coverage = _interval_coverage(start, end, qa_start, qa_end)
        if start <= qa_start + 2.5 and end >= qa_end - 2.5 and coverage >= 0.72:
            qa_bridge = True
            qa_boundary_basis = str(candidate.get("boundary_basis") or "sem_diarização")
            qa_boundary_review_required = bool(candidate.get("needs_speaker_review") or candidate.get("overlap_suspected"))
            break

    # A window computed in the context stage is the strongest evidence, but its
    # absence is not evidence of absence: those windows are proposed by their own
    # heuristic and a selector rarely lands on one edge to edge. When the clip
    # itself contains the interviewer's turn and enough of the answer, the bridge
    # is there to be heard, and refusing to render it holds back exactly the clips
    # that carry a question.
    if not qa_bridge and local_bridge:
        qa_bridge = True
        qa_boundary_basis = local_basis

    if not overlaps:
        coherence = 35.0
    elif len(overlaps) == 1:
        coherence = 100.0
    else:
        chapter_indexes = [int(chapter.get("index", 0)) for chapter, _ in overlaps]
        contiguous = chapter_indexes == list(range(min(chapter_indexes), max(chapter_indexes) + 1))
        covered = sum(overlap for _, overlap in overlaps)
        gaps = _chapter_gaps(overlaps)
        coherence = 84.0 if contiguous and not gaps else 52.0
        if covered < max(1.0, end - start) * 0.55:
            coherence -= 12.0

    if qa_bridge:
        coherence = min(100.0, coherence + 8.0)

    result.update({
        "editorial_chapter_available": True,
        "editorial_chapter_ids": ids,
        "chapter_count": len(ids),
        "chapter_primary_id": ids[0] if ids else None,
        "chapter_coherence_score": round(max(0.0, min(100.0, coherence)), 1),
        "chapter_crosses_boundary": len(ids) > 1,
        "qa_bridge": qa_bridge,
        "qa_boundary_basis": qa_boundary_basis,
        "qa_boundary_review_required": qa_boundary_review_required,
        "chapter_topics": [chapter.get("label", "") for chapter, _ in overlaps],
    })
    _attach_nearest_hook(result, hook_candidates)
    return result


def _attach_nearest_hook(clip: dict, hook_candidates: list[dict] | None) -> None:
    """Attach only the closest hook evidence; never change clip timestamps."""
    if not isinstance(hook_candidates, list) or not hook_candidates:
        clip.setdefault("contextual_hook", None)
        clip.setdefault("hook_review_required", False)
        return
    start = float(clip.get("start", 0) or 0)
    end = float(clip.get("end", start) or start)
    ranked = []
    for candidate in hook_candidates:
        try:
            hook_start = float(candidate.get("start", 0) or 0)
            hook_end = float(candidate.get("end", hook_start) or hook_start)
        except (TypeError, ValueError):
            continue
        overlap = _interval_overlap(start, end, hook_start, hook_end)
        distance = 0.0 if overlap > 0 else min(abs(start - hook_end), abs(hook_start - end))
        ranked.append((0 if overlap > 0 else 1, distance, -float(candidate.get("score", 0) or 0), candidate))
    if not ranked:
        clip.setdefault("contextual_hook", None)
        clip.setdefault("hook_review_required", False)
        return
    _, distance, _, candidate = sorted(ranked, key=lambda item: item[:3])[0]
    clip["contextual_hook"] = {
        "family": candidate.get("family", "outro"),
        "hook_text": candidate.get("hook_text", ""),
        "score": candidate.get("score", 0),
        "start": candidate.get("start", 0),
        "end": candidate.get("end", 0),
        "payoff_confirmed": bool(candidate.get("payoff_confirmed")),
        "audio_signal": candidate.get("audio_signal") or {"available": False},
        "campaign_hub_prior": candidate.get("campaign_hub_prior"),
    }
    clip["hook_distance_seconds"] = round(float(distance), 3)
    clip["hook_review_required"] = bool(candidate.get("needs_visual_review") or candidate.get("needs_speaker_review"))


def _normalize_segments(segments: list[dict]) -> list[dict]:
    normalized = []
    for index, source in enumerate(segments or []):
        if not isinstance(source, dict):
            continue
        try:
            start = float(source.get("start", 0) or 0)
            end = float(source.get("end", start) or start)
        except (TypeError, ValueError):
            continue
        if end <= start:
            end = start + 0.1
        normalized.append({**source, "start": start, "end": end, "segment_index": index})
    return normalized


def _bridge_ranges(candidates: list[dict]) -> list[tuple[float, float]]:
    ranges = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        try:
            start = float(candidate.get("start", 0) or 0)
            end = float(candidate.get("end", start) or start)
        except (TypeError, ValueError):
            continue
        if end > start:
            ranges.append((start, end))
    return ranges


def _inside_bridge(timepoint: float, bridges: list[tuple[float, float]]) -> bool:
    return any(start - 0.01 <= timepoint <= end + 0.01 for start, end in bridges)


def _interval_overlap(first_start: float, first_end: float, second_start: float, second_end: float) -> float:
    return max(0.0, min(first_end, second_end) - max(first_start, second_start))


def _interval_coverage(first_start: float, first_end: float, second_start: float, second_end: float) -> float:
    target = max(0.001, second_end - second_start)
    return _interval_overlap(first_start, first_end, second_start, second_end) / target


def _chapter_gaps(overlaps: list[tuple[dict, float]]) -> list[float]:
    gaps = []
    ordered = sorted((chapter for chapter, _ in overlaps), key=lambda item: float(item.get("start", 0)))
    for left, right in zip(ordered, ordered[1:]):
        gap = float(right.get("start", 0)) - float(left.get("end", 0))
        if gap > 4.0:
            gaps.append(gap)
    return gaps


def _topic_terms(text: str) -> list[str]:
    stopwords = {
        "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
        "e", "em", "ele", "ela", "esse", "essa", "esta", "eu", "foi", "isso",
        "mais", "na", "nas", "no", "nos", "o", "os", "ou", "para", "por", "pra",
        "que", "se", "sem", "ser", "sobre", "tem", "um", "uma", "vai", "voce", "voces",
    }
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", str(text or "").lower())
    counts = Counter(word for word in words if word not in stopwords and not word.isdigit())
    return [word for word, _ in counts.most_common(6)]
