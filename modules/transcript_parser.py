"""Normalize timestamped transcript formats into the Furia Clips timeline."""

from __future__ import annotations

import re
from typing import Iterable


TIMESTAMP_RE = re.compile(
    r"(?P<stamp>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)"
)
RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)"
)


def parse_timestamp(value: str) -> float:
    """Parse HH:MM:SS.mmm or MM:SS.mmm into seconds."""
    raw = value.strip().replace(",", ".")
    parts = raw.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    raise ValueError(f"Timestamp inválido: {value}")


def _clean_text(text: str) -> str:
    text = re.sub(r"<\d{2}:\d{2}:\d{2}[\.,]\d{3}>\s*", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize(segments: Iterable[dict], duration: float | None = None) -> list[dict]:
    ordered = sorted(
        [s for s in segments if s.get("text") and s.get("start") is not None],
        key=lambda s: float(s["start"]),
    )
    result = []
    for index, item in enumerate(ordered):
        start = max(0.0, float(item["start"]))
        next_start = float(ordered[index + 1]["start"]) if index + 1 < len(ordered) else None
        end = item.get("end")
        if end is None:
            end = next_start if next_start is not None and next_start > start else start + 2.0
        end = max(start + 0.05, float(end))
        if duration is not None:
            end = min(end, max(start + 0.05, float(duration)))
        normalized = {
            "id": index,
            "start": round(start, 3),
            "end": round(end, 3),
            "text": _clean_text(str(item["text"])),
        }
        for key in ("speaker", "source", "confidence"):
            if item.get(key) is not None:
                normalized[key] = item[key]
        result.append(normalized)
    return result


def parse_transcript_text(text: str, duration: float | None = None) -> dict:
    """Parse Tactiq/plain timestamped text, SRT or VTT."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A transcrição está vazia")

    raw = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    range_matches = list(RANGE_RE.finditer(raw))
    if range_matches or "WEBVTT" in raw[:80].upper():
        segments = _parse_ranges(raw)
    else:
        segments = _parse_timestamp_lines(raw)

    normalized = _normalize(segments, duration=duration)
    if not normalized:
        raise ValueError("Nenhum segmento com timestamp reconhecível foi encontrado")
    return {
        "segments": normalized,
        "full_text": " ".join(segment["text"] for segment in normalized),
        "source": "manual",
        "format": detect_format(raw),
        "segment_count": len(normalized),
    }


def _parse_timestamp_lines(raw: str) -> list[dict]:
    segments = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.upper() == "WEBVTT":
            continue
        match = TIMESTAMP_RE.match(line)
        if not match:
            continue
        text = line[match.end():].strip(" -\t")
        if text:
            segments.append({"start": parse_timestamp(match.group("stamp")), "text": text})
    return segments


def _parse_ranges(raw: str) -> list[dict]:
    lines = raw.split("\n")
    segments = []
    index = 0
    while index < len(lines):
        match = RANGE_RE.search(lines[index])
        if not match:
            index += 1
            continue
        text_lines = []
        index += 1
        while index < len(lines) and not RANGE_RE.search(lines[index]):
            line = lines[index].strip()
            if line and not line.isdigit() and line.upper() != "WEBVTT":
                text_lines.append(line)
            index += 1
        text = " ".join(text_lines).strip()
        if text:
            segments.append({
                "start": parse_timestamp(match.group("start")),
                "end": parse_timestamp(match.group("end")),
                "text": text,
            })
    return segments


def detect_format(raw: str) -> str:
    if "WEBVTT" in raw[:80].upper():
        return "vtt"
    if "-->" in raw:
        return "srt"
    return "tactiq" if any(TIMESTAMP_RE.match(line.strip()) for line in raw.splitlines()) else "timestamped"


def normalize_segment_payload(segments: Iterable[dict], duration: float | None = None) -> dict:
    normalized = _normalize(segments, duration=duration)
    if not normalized:
        raise ValueError("Nenhum segmento válido foi informado")
    return {
        "segments": normalized,
        "full_text": " ".join(segment["text"] for segment in normalized),
        "source": "manual",
        "format": "json",
        "segment_count": len(normalized),
    }


def parse_transcript_file(path: str, duration: float | None = None) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return parse_transcript_text(handle.read(), duration=duration)
