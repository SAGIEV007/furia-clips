"""Persistent, local-only comparison between Furia candidates and Chub highlights.

The benchmark is deliberately an observation layer. It does not change ranking or
approve a clip automatically; it records where the current candidates cover, miss,
or need review against an authorized Campaign Hub reference.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BENCHMARK_VERSION = "b354-v1"
DEFAULT_BENCHMARK_DIR = Path(
    os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
) / "benchmarks"
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.:-]+")


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number else default


def _round(value: Any, digits: int = 3) -> float | None:
    number = _float(value)
    return round(number, digits) if number is not None else None


def _interval(value: dict[str, Any], start_keys=("start", "start_s", "start_time"), end_keys=("end", "end_s", "end_time")) -> tuple[float, float] | None:
    start = next((_float(value.get(key)) for key in start_keys if _float(value.get(key)) is not None), None)
    end = next((_float(value.get(key)) for key in end_keys if _float(value.get(key)) is not None), None)
    if start is None or end is None or end <= start:
        return None
    return start, end


def _span_close(duration: float | None, span: float | None) -> bool:
    if duration is None or span is None or span <= 0:
        return False
    return abs(duration - span) <= max(15.0, span * 0.05)


def map_interval_to_local(
    start: float,
    end: float,
    *,
    source_duration: float | None,
    reference_start: float,
    reference_end: float,
) -> dict[str, Any]:
    """Map absolute Chub seconds to a local block timeline when justified."""
    block_span = max(0.0, reference_end - reference_start)
    duration = _float(source_duration)
    if _span_close(duration, block_span):
        local_start = max(0.0, start - reference_start)
        local_end = max(local_start, end - reference_start)
        if duration is not None:
            local_start = min(local_start, duration)
            local_end = min(local_end, duration)
        return {
            "start": _round(local_start),
            "end": _round(local_end),
            "timeline_mapping": "downloaded_block_timeline",
        }
    return {
        "start": _round(start),
        "end": _round(end),
        "timeline_mapping": "source_timeline",
    }


def interval_iou(left: tuple[float, float] | None, right: tuple[float, float] | None) -> float:
    if not left or not right:
        return 0.0
    intersection = max(0.0, min(left[1], right[1]) - max(left[0], right[0]))
    union = max(left[1], right[1]) - min(left[0], right[0])
    return intersection / union if union > 0 else 0.0


def _contains(container: tuple[float, float], target: tuple[float, float], tolerance: float = 0.75) -> bool:
    return container[0] <= target[0] + tolerance and container[1] >= target[1] - tolerance


def _classification(best: dict[str, Any] | None) -> str:
    if not best or not best.get("candidate_id"):
        return "campaign_hub_better"
    if best.get("coverage") and best.get("iou", 0.0) >= 0.45 and best.get("boundary_error_s", 999.0) <= 8.0:
        flags = best.get("review_flags") or {}
        if flags.get("context_complete") is False or flags.get("payoff_complete") is False:
            return "both_need_review"
        return "furia_better"
    if best.get("iou", 0.0) < 0.25 or best.get("boundary_error_s", 999.0) > 15.0:
        return "campaign_hub_better"
    return "both_need_review"


def _candidate_view(candidate: dict[str, Any], interval: tuple[float, float]) -> dict[str, Any]:
    flags = candidate.get("review_flags")
    if not isinstance(flags, dict):
        flags = {}
    return {
        "candidate_id": str(candidate.get("id") or candidate.get("clip_id") or ""),
        "start": _round(interval[0]),
        "end": _round(interval[1]),
        "duration": _round(interval[1] - interval[0]),
        "score": _round(candidate.get("score", candidate.get("viral_score")), 2),
        "transcript": " ".join(str(candidate.get("transcript") or candidate.get("text") or "").split())[:800],
        "review_flags": {
            key: flags.get(key)
            for key in (
                "context_complete",
                "payoff_complete",
                "starts_mid_sentence",
                "qa_boundary_review_required",
                "speaker_review_required",
                "technical_gate_status",
            )
            if key in flags
        },
    }


def compare_candidates(
    block: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    source_duration: float | None = None,
    source_name: str = "",
    benchmark_version: str = BENCHMARK_VERSION,
) -> dict[str, Any]:
    """Build a stable comparison payload for one Campaign Hub block."""
    reference_start = _float(block.get("start", block.get("start_s")), 0.0) or 0.0
    reference_end = _float(block.get("end", block.get("end_s")), reference_start) or reference_start
    if reference_end <= reference_start:
        raise ValueError("Bloco de benchmark sem intervalo válido.")
    mapped_references = []
    for index, raw in enumerate(block.get("highlights") or []):
        if not isinstance(raw, dict):
            continue
        absolute = _interval(raw, ("start_s", "start", "start_time"), ("end_s", "end", "end_time"))
        if not absolute:
            continue
        mapped = map_interval_to_local(
            absolute[0], absolute[1],
            source_duration=source_duration,
            reference_start=reference_start,
            reference_end=reference_end,
        )
        mapped_references.append({
            "highlight_id": str(raw.get("id") or f"highlight-{index + 1}"),
            "text": " ".join(str(raw.get("text") or "").split())[:800],
            "reason": " ".join(str(raw.get("reason") or "").split())[:800],
            "absolute_start": _round(absolute[0]),
            "absolute_end": _round(absolute[1]),
            "local_start": mapped["start"],
            "local_end": mapped["end"],
            "timeline_mapping": mapped["timeline_mapping"],
        })
    normalized_candidates = []
    for index, raw in enumerate(candidates or []):
        if not isinstance(raw, dict):
            continue
        interval = _interval(raw)
        if not interval:
            continue
        item = dict(raw)
        item.setdefault("id", f"candidate-{index + 1}")
        normalized_candidates.append((item, interval))

    comparisons = []
    for reference in mapped_references:
        target = (reference["local_start"], reference["local_end"])
        matches = []
        for candidate, candidate_interval in normalized_candidates:
            iou = interval_iou(candidate_interval, target)
            coverage = _contains(candidate_interval, target)
            start_error = abs(candidate_interval[0] - target[0])
            end_error = abs(candidate_interval[1] - target[1])
            boundary_error = (start_error + end_error) / 2.0
            view = _candidate_view(candidate, candidate_interval)
            matches.append({
                **view,
                "iou": round(iou, 4),
                "coverage": coverage,
                "start_error_s": round(start_error, 3),
                "end_error_s": round(end_error, 3),
                "boundary_error_s": round(boundary_error, 3),
            })
        matches.sort(key=lambda item: (-item["iou"], item["boundary_error_s"], str(item["candidate_id"])))
        best = matches[0] if matches else None
        comparison = {
            **reference,
            "best": best,
            "classification": _classification(best),
            "candidate_matches": matches[:5],
        }
        comparisons.append(comparison)

    covered = sum(1 for item in comparisons if item.get("best", {}).get("coverage"))
    ious = [item["best"]["iou"] for item in comparisons if item.get("best")]
    errors = [item["best"]["boundary_error_s"] for item in comparisons if item.get("best")]
    classifications = {
        key: sum(1 for item in comparisons if item.get("classification") == key)
        for key in ("furia_better", "campaign_hub_better", "both_need_review")
    }
    intervals = [interval for _, interval in normalized_candidates]
    duplicate_candidates = 0
    for index, current in enumerate(intervals):
        if any(interval_iou(current, previous) >= 0.8 for previous in intervals[:index]):
            duplicate_candidates += 1

    return {
        "benchmark_id": f"{block.get('id') or block.get('block_id')}-{benchmark_version}",
        "benchmark_version": benchmark_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "block": {
            "id": block.get("id") or block.get("block_id"),
            "title": block.get("title") or "",
            "source_video_id": block.get("video_id") or "",
            "renan_speaking": block.get("renan_speaking"),
            "start": _round(reference_start),
            "end": _round(reference_end),
            "duration": _round(reference_end - reference_start),
            "highlight_count": len(mapped_references),
            "risk_flags": block.get("risk_flags") or block.get("riskFlags") or [],
        },
        "source": {
            "name": Path(str(source_name or "")).name[:180],
            "duration_s": _round(source_duration),
            "timeline_mapping": mapped_references[0]["timeline_mapping"] if mapped_references else "unknown",
        },
        "candidate_count": len(normalized_candidates),
        "references": mapped_references,
        "comparisons": comparisons,
        "metrics": {
            "reference_count": len(comparisons),
            "covered_count": covered,
            "coverage_recall": round(covered / len(comparisons), 4) if comparisons else 0.0,
            "mean_best_iou": round(sum(ious) / len(ious), 4) if ious else 0.0,
            "mean_boundary_error_s": round(sum(errors) / len(errors), 3) if errors else None,
            "duplicate_candidates": duplicate_candidates,
            "classifications": classifications,
        },
    }


def _benchmark_dir(path: str | os.PathLike[str] | None = None) -> Path:
    target = Path(path).expanduser() if path else DEFAULT_BENCHMARK_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_filename(value: str) -> str:
    return _SAFE_ID.sub("_", str(value or "benchmark"))[:180].strip("._") or "benchmark"


def save_benchmark(payload: dict[str, Any], path: str | os.PathLike[str] | None = None) -> Path:
    if not isinstance(payload, dict) or not payload.get("benchmark_id"):
        raise ValueError("Payload de benchmark inválido.")
    directory = _benchmark_dir(path)
    target = directory / f"{_safe_filename(payload['benchmark_id'])}.json"
    fd, temporary = tempfile.mkstemp(prefix=".benchmark-", suffix=".json", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def load_benchmark(benchmark_id: str, path: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    directory = _benchmark_dir(path)
    target = directory / f"{_safe_filename(benchmark_id)}.json"
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def list_benchmarks(path: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    directory = _benchmark_dir(path)
    items = []
    for target in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
            items.append({
                "benchmark_id": payload.get("benchmark_id", target.stem),
                "benchmark_version": payload.get("benchmark_version", ""),
                "created_at": payload.get("created_at", ""),
                "candidate_count": payload.get("candidate_count", 0),
                "metrics": metrics,
            })
    return items[:100]
