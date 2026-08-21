"""Métricas verificáveis para avaliar candidatos de clipping.

O módulo não prevê viralização. Ele compara intervalos produzidos pelo Furia
com referências editoriais fornecidas pelo editor, pelo Garimpo ou por uma
anotação autorizada. Sem referências, não fabrica qualidade nem baseline.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Iterable


def _interval(item: Any) -> tuple[float, float] | None:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        start_value, end_value = item[0], item[1]
    elif isinstance(item, dict):
        start_value = item.get("start")
        end_value = item.get("end")
        if start_value is None:
            start_value = item.get("startS")
        if end_value is None:
            end_value = item.get("endS")
        if start_value is None:
            start_value = item.get("hook_start")
        if end_value is None:
            end_value = item.get("hook_end")
    else:
        return None
    try:
        start = float(start_value)
        end = float(end_value)
    except (TypeError, ValueError):
        return None
    if start < 0 or end <= start:
        return None
    return start, end


def interval_iou(left: Any, right: Any) -> float:
    """Return temporal intersection-over-union for two valid intervals."""
    first = _interval(left)
    second = _interval(right)
    if first is None or second is None:
        return 0.0
    intersection = max(0.0, min(first[1], second[1]) - max(first[0], second[0]))
    union = max(first[1], second[1]) - min(first[0], second[0])
    return round(intersection / union, 6) if union > 0 else 0.0


def boundary_errors(predicted: Any, reference: Any) -> dict[str, float] | None:
    """Return absolute start/end errors in seconds for a matched pair."""
    first = _interval(predicted)
    second = _interval(reference)
    if first is None or second is None:
        return None
    return {
        "start_error_seconds": round(abs(first[0] - second[0]), 3),
        "end_error_seconds": round(abs(first[1] - second[1]), 3),
    }


def _normalize_items(items: Iterable[Any] | None) -> list[tuple[int, tuple[float, float]]]:
    normalized = []
    for index, item in enumerate(items or []):
        interval = _interval(item)
        if interval is not None:
            normalized.append((index, interval))
    return normalized


def _greedy_matches(
    predictions: list[tuple[int, tuple[float, float]]],
    references: list[tuple[int, tuple[float, float]]],
    threshold: float,
) -> list[dict[str, float | int]]:
    pairs = []
    for prediction_index, prediction in predictions:
        for reference_index, reference in references:
            iou = interval_iou(prediction, reference)
            if iou >= threshold:
                pairs.append((iou, prediction_index, reference_index, prediction, reference))
    pairs.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_predictions: set[int] = set()
    used_references: set[int] = set()
    matches = []
    for iou, prediction_index, reference_index, prediction, reference in pairs:
        if prediction_index in used_predictions or reference_index in used_references:
            continue
        errors = boundary_errors(prediction, reference) or {}
        used_predictions.add(prediction_index)
        used_references.add(reference_index)
        matches.append({
            "prediction_index": prediction_index,
            "reference_index": reference_index,
            "iou": round(float(iou), 6),
            **errors,
        })
    return matches


def _duplicate_rate(predictions: list[tuple[int, tuple[float, float]]], threshold: float) -> float:
    if len(predictions) < 2:
        return 0.0
    duplicate_count = 0
    for index, (_, left) in enumerate(predictions):
        has_duplicate = any(
            interval_iou(left, right) >= threshold
            for other_index, (_, right) in enumerate(predictions)
            if other_index != index
        )
        if has_duplicate:
            duplicate_count += 1
    return round(duplicate_count / len(predictions), 6)


def _union_length(intervals: Iterable[tuple[float, float]]) -> float:
    ordered = sorted((float(start), float(end)) for start, end in intervals if end > start)
    if not ordered:
        return 0.0
    total = 0.0
    active_start, active_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= active_end:
            active_end = max(active_end, end)
            continue
        total += active_end - active_start
        active_start, active_end = start, end
    return total + active_end - active_start


def _coverage_seconds(
    predictions: list[tuple[int, tuple[float, float]]],
    references: list[tuple[int, tuple[float, float]]],
) -> dict[str, float]:
    reference_intervals = [interval for _, interval in references]
    prediction_intervals = [interval for _, interval in predictions]
    total_reference_seconds = _union_length(reference_intervals)
    covered_parts = []
    for reference_start, reference_end in reference_intervals:
        for prediction_start, prediction_end in prediction_intervals:
            start = max(reference_start, prediction_start)
            end = min(reference_end, prediction_end)
            if end > start:
                covered_parts.append((start, end))
    covered_reference_seconds = _union_length(covered_parts)
    return {
        "reference_seconds": round(total_reference_seconds, 3),
        "covered_reference_seconds": round(covered_reference_seconds, 3),
        "coverage_ratio": round(covered_reference_seconds / total_reference_seconds, 6)
        if total_reference_seconds > 0 else 0.0,
    }


def evaluate_temporal_quality(
    predictions: Iterable[Any] | None,
    references: Iterable[Any] | None,
    *,
    iou_thresholds: Iterable[float] = (0.3, 0.5, 0.7),
    boundary_tolerances: Iterable[float] = (2.0, 5.0),
    duplicate_iou: float = 0.8,
    max_predictions: int | None = None,
) -> dict[str, Any]:
    """Evaluate predicted clip intervals against supplied editorial references.

    The input order is preserved for top-k evaluation. Invalid intervals are
    discarded and reported, while no quality score is emitted for an empty
    reference set. ``references`` must come from real editorial review or an
    authorized benchmark; this function never creates a baseline itself.
    """
    raw_predictions = list(predictions or [])
    raw_references = list(references or [])
    normalized_predictions = _normalize_items(raw_predictions)
    normalized_references = _normalize_items(raw_references)
    if max_predictions is not None:
        try:
            limit = max(0, int(max_predictions))
        except (TypeError, ValueError):
            limit = len(normalized_predictions)
        normalized_predictions = normalized_predictions[:limit]

    prediction_count = len(normalized_predictions)
    reference_count = len(normalized_references)
    invalid_prediction_count = len(raw_predictions) - len(_normalize_items(raw_predictions))
    invalid_reference_count = len(raw_references) - len(normalized_references)
    result: dict[str, Any] = {
        "prediction_count": prediction_count,
        "reference_count": reference_count,
        "invalid_prediction_count": invalid_prediction_count,
        "invalid_reference_count": invalid_reference_count,
        "basis": "supplied_editorial_references" if reference_count else "no_reference",
        "duplicate_rate": _duplicate_rate(normalized_predictions, duplicate_iou),
        "duplicate_iou_threshold": duplicate_iou,
        "iou": {},
        "hit_at_k": {},
        "coverage": {"reference_seconds": 0.0, "covered_reference_seconds": 0.0, "coverage_ratio": 0.0},
        "boundary": {"matched_at_iou": 0.5, "match_count": 0},
        "matches_at_iou_0_5": [],
    }
    if not reference_count:
        return result

    normalized_thresholds = []
    for value in iou_thresholds:
        try:
            threshold = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            continue
        if threshold not in normalized_thresholds:
            normalized_thresholds.append(threshold)
    for threshold in normalized_thresholds:
        matches = _greedy_matches(normalized_predictions, normalized_references, threshold)
        matched_count = len(matches)
        result["iou"][str(threshold)] = {
            "matched_count": matched_count,
            "precision": round(matched_count / prediction_count, 6) if prediction_count else 0.0,
            "recall": round(matched_count / reference_count, 6),
            "matches": matches,
        }

    result["coverage"] = _coverage_seconds(normalized_predictions, normalized_references)
    for limit in (1, 3, 5, 10):
        top_predictions = normalized_predictions[:limit]
        top_matches = _greedy_matches(top_predictions, normalized_references, 0.5)
        result["hit_at_k"][str(limit)] = {
            "hit": bool(top_matches),
            "matched_count": len(top_matches),
            "recall": round(len(top_matches) / reference_count, 6),
        }

    strict_matches = _greedy_matches(normalized_predictions, normalized_references, 0.5)
    result["matches_at_iou_0_5"] = strict_matches
    result["boundary"]["match_count"] = len(strict_matches)
    if strict_matches:
        start_errors = [float(item["start_error_seconds"]) for item in strict_matches]
        end_errors = [float(item["end_error_seconds"]) for item in strict_matches]
        ious = [float(item["iou"]) for item in strict_matches]
        result["boundary"].update({
            "mean_start_error_seconds": round(sum(start_errors) / len(start_errors), 3),
            "mean_end_error_seconds": round(sum(end_errors) / len(end_errors), 3),
            "median_start_error_seconds": round(float(median(start_errors)), 3),
            "median_end_error_seconds": round(float(median(end_errors)), 3),
            "mean_iou": round(sum(ious) / len(ious), 6),
        })
        tolerances = []
        for value in boundary_tolerances:
            try:
                tolerance = max(0.0, float(value))
            except (TypeError, ValueError):
                continue
            if tolerance in tolerances:
                continue
            tolerances.append(tolerance)
            hits = sum(1 for start, end in zip(start_errors, end_errors) if start <= tolerance and end <= tolerance)
            result["boundary"][f"hit_rate_{str(tolerance).replace('.', '_')}s"] = round(hits / len(strict_matches), 6)
    return result
