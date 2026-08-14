#!/usr/bin/env python3
"""Audita transcrições timestampadas sem modificar o arquivo de origem."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

LINE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)\s+(.*)$")


def seconds(hours: str, minutes: str, value: str) -> float:
    return int(hours) * 3600 + int(minutes) * 60 + float(value)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw_lines = args.input.read_text(encoding="utf-8-sig").splitlines()
    segments = []
    invalid = []
    for number, line in enumerate(raw_lines, 1):
        match = LINE.match(line.strip())
        if not match:
            invalid.append({"line": number, "content": line[:160]})
            continue
        timestamp = seconds(match.group(1), match.group(2), match.group(3))
        text = match.group(4).strip()
        segments.append({"line": number, "start": timestamp, "text": text, "normalized": normalize(text)})

    exact_duplicates = []
    overlap_count = 0
    backwards = 0
    small_gap_count = 0
    entity_lines = []
    previous_time = None
    previous_text = None
    for index, segment in enumerate(segments):
        if previous_time is not None:
            gap = segment["start"] - previous_time
            if gap < 0:
                backwards += 1
            if gap <= 0.02:
                small_gap_count += 1
        if previous_text and segment["normalized"] == previous_text:
            exact_duplicates.append({"line": segment["line"], "timestamp": segment["start"], "text": segment["text"]})
        if "&gt;" in segment["text"] or "Ã" in segment["text"] or "&amp;" in segment["text"]:
            entity_lines.append({"line": segment["line"], "timestamp": segment["start"], "text": segment["text"]})
        previous_time = segment["start"]
        previous_text = segment["normalized"]

    nonempty = [segment for segment in segments if segment["normalized"]]
    first = nonempty[0]["start"] if nonempty else 0
    last = nonempty[-1]["start"] if nonempty else 0
    repeated_prefixes = Counter(segment["normalized"][:45] for segment in nonempty if len(segment["normalized"]) >= 20)
    top_prefixes = [
        {"prefix": prefix, "count": count}
        for prefix, count in repeated_prefixes.most_common(12)
        if count >= 4
    ]

    report = {
        "source": str(args.input),
        "line_count": len(raw_lines),
        "timestamped_segments": len(segments),
        "invalid_lines": invalid[:25],
        "first_timestamp_seconds": first,
        "last_timestamp_seconds": last,
        "coverage_minutes": round((last - first) / 60, 2),
        "consecutive_exact_duplicates": len(exact_duplicates),
        "duplicate_examples": exact_duplicates[:20],
        "backwards_timestamps": backwards,
        "sub_20ms_or_equal_gaps": small_gap_count,
        "encoding_or_html_artifacts": len(entity_lines),
        "artifact_examples": entity_lines[:25],
        "frequently_repeated_prefixes": top_prefixes,
        "empty_segments": len(segments) - len(nonempty),
        "structural_verdict": "needs_cleanup" if exact_duplicates or backwards or entity_lines else "structurally_clean",
        "semantic_note": "A auditoria mede estrutura e artefatos. Exatidão factual e correspondência com o áudio exigem revisão humana ou comparação direta com o vídeo.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
