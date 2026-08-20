#!/usr/bin/env python3
"""Score a Chub benchmark result against authorized Acervo highlights.

The old exploratory scorer read a fixed ``benchmark_rich_result.json`` path,
which could silently score a stale run. This command requires the benchmark
result explicitly and keeps the reference highlights in a separate file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def load_highlights(path: str | Path) -> list[tuple[float, float]]:
    payload = _load_json(path)
    blocks = payload.get("structuredContent") or payload.get("content") or payload
    if isinstance(blocks, list):
        blocks = blocks[0] if blocks else {}
    if isinstance(blocks, dict) and isinstance(blocks.get("text"), str):
        try:
            blocks = json.loads(blocks["text"])
        except json.JSONDecodeError:
            blocks = {}
    highlights: list[tuple[float, float]] = []
    for block in (blocks.get("items") or []) if isinstance(blocks, dict) else []:
        for row in block.get("highlights") or []:
            if not isinstance(row, dict):
                continue
            try:
                start = float(row.get("startS") or 0)
                end = float(row.get("endS") or 0)
            except (TypeError, ValueError):
                continue
            if end > start:
                highlights.append((start, end))
    return highlights


def iou(first: tuple[float, float], second: tuple[float, float]) -> float:
    left = max(first[0], second[0])
    right = min(first[1], second[1])
    overlap = max(0.0, right - left)
    union = max(first[1], second[1]) - min(first[0], second[0])
    return overlap / union if union else 0.0


def score(intervals: list[tuple[float, float]], highlights: list[tuple[float, float]], threshold: float) -> dict[str, Any]:
    hits = sum(
        1
        for highlight in highlights
        if max((iou(highlight, candidate) for candidate in intervals), default=0.0) >= threshold
    )
    return {
        "hits": hits,
        "total": len(highlights),
        "recall": round(hits / len(highlights), 4) if highlights else 0.0,
    }


def score_benchmark(benchmark: dict[str, Any], highlights: list[tuple[float, float]]) -> dict[str, Any]:
    conditions = []
    for condition in benchmark.get("conditions") or []:
        all_intervals = [tuple(item) for item in condition.get("all_intervals", [])]
        guided_intervals = [tuple(item) for item in condition.get("all_guided_intervals", [])]
        conditions.append({
            "label": condition.get("label", ""),
            "candidate_count": len(all_intervals),
            "guided_count": len(guided_intervals),
            "all_iou_recall_0_10": score(all_intervals, highlights, 0.10),
            "guided_iou_recall_0_10": score(guided_intervals, highlights, 0.10),
            "all_iou_recall_0_25": score(all_intervals, highlights, 0.25),
            "guided_iou_recall_0_25": score(guided_intervals, highlights, 0.25),
        })
    return {"highlight_count": len(highlights), "conditions": conditions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, help="JSON produced by benchmark_chub_rich_3xj.py")
    parser.add_argument("--blocks", required=True, help="Acervo blocks JSON containing reference highlights")
    args = parser.parse_args()
    print(json.dumps(score_benchmark(_load_json(args.benchmark), load_highlights(args.blocks)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
