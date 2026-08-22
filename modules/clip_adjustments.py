"""Safe, non-destructive clip boundary adjustments.

The helper keeps the original media timeline canonical and only returns a derived
copy of a candidate clip. It can snap boundaries to transcript segments when the
requested point is close enough, while preserving a minimum usable duration.
"""

from __future__ import annotations

from copy import deepcopy
import math


def adjust_clip_bounds(
    clip: dict,
    *,
    start: float | None = None,
    end: float | None = None,
    transcript_segments: list[dict] | None = None,
    duration: float | None = None,
    snap_tolerance: float = 2.0,
    min_duration: float = 3.0,
) -> dict:
    """Return a validated copy of ``clip`` with optional boundary snapping.

    The input object is never modified. ``start`` and ``end`` are interpreted as
    original-video seconds. Transcript snapping is conservative: a requested
    start is snapped to a nearby segment start and a requested end to a nearby
    segment end only when the distance is within ``snap_tolerance``.
    """
    if not isinstance(clip, dict):
        raise ValueError("Clip inválido")

    original_start = _number(clip.get("start", 0.0), "start")
    original_end = _number(clip.get("end", original_start), "end")
    if original_end <= original_start:
        raise ValueError("O fim original deve ser maior que o início")

    requested_start = original_start if start is None else _number(start, "start")
    requested_end = original_end if end is None else _number(end, "end")
    if requested_end <= requested_start:
        raise ValueError("O fim deve ser maior que o início")

    limit = _positive_or_none(duration)
    if limit is not None:
        requested_start = min(max(0.0, requested_start), limit)
        requested_end = min(max(0.0, requested_end), limit)
    if requested_end <= requested_start:
        raise ValueError("Os limites ajustados não formam um intervalo válido")

    adjusted_start = _snap_boundary(requested_start, transcript_segments, "start", snap_tolerance)
    adjusted_end = _snap_boundary(requested_end, transcript_segments, "end", snap_tolerance)
    if limit is not None:
        adjusted_start = min(max(0.0, adjusted_start), limit)
        adjusted_end = min(max(0.0, adjusted_end), limit)

    minimum = max(0.1, float(min_duration))
    if adjusted_end - adjusted_start < minimum:
        adjusted_start, adjusted_end = _expand_interval(
            adjusted_start, adjusted_end, minimum, limit
        )
    if adjusted_end <= adjusted_start or adjusted_end - adjusted_start < minimum:
        raise ValueError("Não foi possível preservar a duração mínima dentro da fonte")

    result = deepcopy(clip)
    result.update({
        "start": round(adjusted_start, 3),
        "end": round(adjusted_end, 3),
        "duration": round(adjusted_end - adjusted_start, 3),
        "boundary_adjustment": {
            "requested_start": round(requested_start, 3),
            "requested_end": round(requested_end, 3),
            "snapped_start": adjusted_start != requested_start,
            "snapped_end": adjusted_end != requested_end,
            "source": "transcript" if transcript_segments and (adjusted_start != requested_start or adjusted_end != requested_end) else "manual",
        },
    })
    return result


def _number(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} inválido") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} deve ser um número finito")
    if number < 0:
        raise ValueError(f"{field} não pode ser negativo")
    return number


def _positive_or_none(value: object) -> float | None:
    if value is None:
        return None
    number = _number(value, "duration")
    return number if number > 0 else None


def _snap_boundary(
    value: float,
    segments: list[dict] | None,
    side: str,
    tolerance: float,
) -> float:
    if not isinstance(segments, list) or not segments:
        return value
    candidates = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        key = "start" if side == "start" else "end"
        try:
            boundary = float(segment.get(key))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(boundary) or boundary < 0:
            continue
        candidates.append(boundary)
    if not candidates:
        return value
    try:
        tolerance_value = float(tolerance)
    except (TypeError, ValueError):
        tolerance_value = 0.0
    if not math.isfinite(tolerance_value):
        tolerance_value = 0.0
    nearest = min(candidates, key=lambda boundary: abs(boundary - value))
    return nearest if abs(nearest - value) <= max(0.0, tolerance_value) else value


def _expand_interval(start: float, end: float, minimum: float, limit: float | None) -> tuple[float, float]:
    center = (start + end) / 2.0
    half = minimum / 2.0
    new_start = center - half
    new_end = center + half
    if new_start < 0:
        new_end -= new_start
        new_start = 0.0
    if limit is not None and new_end > limit:
        shift = new_end - limit
        new_start -= shift
        new_end = limit
        if new_start < 0:
            new_start = 0.0
    return new_start, new_end
