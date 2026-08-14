"""Normalize timestamped transcript formats into the Furia Clips timeline."""

from __future__ import annotations

import html
import re
from typing import Iterable


TIMESTAMP_RE = re.compile(
    r"(?P<stamp>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)"
)
INLINE_TIMESTAMP_RE = re.compile(
    r"(?<![\w:])(?P<stamp>\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?)(?=\s|[-–—:)>\]])"
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
    text = html.unescape(text)
    text = re.sub(r"<\d{2}:\d{2}:\d{2}[\.,]\d{3}>\s*", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    # Auto-captions may encode speaker cues as literal arrows; this is not
    # reliable diarization and should not pollute the editorial transcript.
    text = re.sub(r"(?:^|\s)(?:>>|>)\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"\S+", _clean_text(text))


def _progressive_delta(previous: str, current: str) -> str | None:
    """Return newly revealed words from an overlapping caption, if confident."""
    previous_words = _word_tokens(previous)
    current_words = _word_tokens(current)
    previous_folded = [word.lower() for word in previous_words]
    current_folded = [word.lower() for word in current_words]
    if not previous_words or not current_words:
        return None
    if previous_folded == current_folded:
        return ""
    if current_folded[: len(previous_folded)] == previous_folded and (
        len(previous_words) >= 2 or len(current_words) > 1
    ):
        return " ".join(current_words[len(previous_words) :])
    max_overlap = min(len(previous_words), len(current_words))
    for overlap in range(max_overlap, 2, -1):
        if previous_folded[-overlap:] == current_folded[:overlap]:
            return " ".join(current_words[overlap:])
    return None


def _deduplicate_progressive_segments(segments: Iterable[dict]) -> list[dict]:
    """Collapse rolling-window captions without dropping independent short replies."""
    cleaned: list[dict] = []
    for raw in segments:
        item = dict(raw)
        item["text"] = _clean_text(str(item.get("text", "")))
        if not item["text"]:
            continue
        if not cleaned:
            cleaned.append(item)
            continue
        previous = cleaned[-1]
        delta = _progressive_delta(str(previous.get("text", "")), item["text"])
        if delta is None:
            cleaned.append(item)
            continue
        if item.get("end") is not None and previous.get("end") is not None:
            previous["end"] = max(float(previous["end"]), float(item["end"]))
        if delta:
            item["text"] = _clean_text(delta)
            cleaned.append(item)
    return cleaned


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
            if next_start is not None and next_start > start:
                end = next_start
            elif len(ordered) == 1 and duration is not None and float(duration) > start:
                end = float(duration)
            else:
                end = start + 2.0
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

    normalized = _normalize(_deduplicate_progressive_segments(segments), duration=duration)
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

    # Tactiq and copied captions sometimes arrive as one wrapped paragraph,
    # with timestamps inline instead of one timestamp per line.
    if len(segments) <= 1:
        matches = list(INLINE_TIMESTAMP_RE.finditer(raw))
        if len(matches) > 1:
            inline_segments = []
            for index, match in enumerate(matches):
                next_start = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
                text = raw[match.end():next_start].strip(" -–—:|[]()\t\n")
                if text:
                    inline_segments.append({
                        "start": parse_timestamp(match.group("stamp")),
                        "text": text,
                    })
            if len(inline_segments) > len(segments):
                segments = inline_segments
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
    normalized = _normalize(_deduplicate_progressive_segments(segments), duration=duration)
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
