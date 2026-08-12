"""Timeline utilities for mapping derived media back to the original video.

The original media timeline is canonical. Derived media, such as a version with
silences removed, is represented as contiguous segments that retain their
original start/end times. This module is intentionally independent from Flask
and FFmpeg so it can be tested deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class TimelineSegment:
    """A contiguous relation between original and derived media timelines."""

    original_start: float
    original_end: float
    derived_start: float
    derived_end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.original_end - self.original_start)

    def __post_init__(self) -> None:
        if self.original_start < 0 or self.derived_start < 0:
            raise ValueError("Timeline starts must be non-negative")
        if self.original_end <= self.original_start:
            raise ValueError("Original segment must have positive duration")
        if self.derived_end <= self.derived_start:
            raise ValueError("Derived segment must have positive duration")
        original_duration = self.original_end - self.original_start
        derived_duration = self.derived_end - self.derived_start
        if abs(original_duration - derived_duration) > 1e-3:
            raise ValueError("Timeline segment durations must match")


class TimelineMap:
    """Convert intervals between the original and a derived timeline."""

    def __init__(self, segments: Iterable[TimelineSegment]):
        ordered = sorted(list(segments), key=lambda s: s.derived_start)
        if not ordered:
            raise ValueError("A timeline map needs at least one segment")
        self.segments: Tuple[TimelineSegment, ...] = tuple(ordered)
        self._validate_order()

    @classmethod
    def from_original_segments(
        cls, speech_segments: Iterable[dict], padding: float = 0.0
    ) -> "TimelineMap":
        """Build a derived timeline from original speech intervals.

        ``speech_segments`` must contain ``start`` and ``end`` in original
        seconds. Padding is clamped so adjacent segments never overlap.
        """

        normalized = []
        for item in speech_segments:
            start = float(item["start"])
            end = float(item["end"])
            if end <= start:
                continue
            normalized.append((start, end))

        if not normalized:
            raise ValueError("No valid original segments supplied")

        normalized.sort()
        result: List[TimelineSegment] = []
        derived_cursor = 0.0
        previous_end = 0.0
        for index, (start, end) in enumerate(normalized):
            if index and start < previous_end:
                start = previous_end
            if end <= start:
                continue
            padded_start = max(previous_end, start - max(0.0, padding))
            padded_end = end + max(0.0, padding)
            if index + 1 < len(normalized):
                next_start = normalized[index + 1][0]
                padded_end = min(padded_end, next_start)
            if padded_end <= padded_start:
                continue
            duration = padded_end - padded_start
            result.append(
                TimelineSegment(
                    original_start=padded_start,
                    original_end=padded_end,
                    derived_start=derived_cursor,
                    derived_end=derived_cursor + duration,
                )
            )
            derived_cursor += duration
            previous_end = end

        return cls(result)

    def _validate_order(self) -> None:
        previous_original_end = -1.0
        previous_derived_end = -1.0
        for segment in self.segments:
            if segment.original_start < previous_original_end - 1e-6:
                raise ValueError("Original timeline segments overlap or are unsorted")
            if segment.derived_start < previous_derived_end - 1e-6:
                raise ValueError("Derived timeline segments overlap or are unsorted")
            previous_original_end = segment.original_end
            previous_derived_end = segment.derived_end

    def derived_to_original(self, start: float, end: float) -> List[Tuple[float, float]]:
        """Map a derived interval to one or more original intervals."""

        if end <= start:
            raise ValueError("Interval end must be greater than start")
        mapped: List[Tuple[float, float]] = []
        for segment in self.segments:
            overlap_start = max(start, segment.derived_start)
            overlap_end = min(end, segment.derived_end)
            if overlap_end <= overlap_start:
                continue
            offset_start = overlap_start - segment.derived_start
            offset_end = overlap_end - segment.derived_start
            mapped.append(
                (
                    segment.original_start + offset_start,
                    segment.original_start + offset_end,
                )
            )
        if not mapped:
            raise ValueError("Derived interval is outside the mapped timeline")
        return mapped

    def original_to_derived(self, start: float, end: float) -> List[Tuple[float, float]]:
        """Map an original interval to one or more derived intervals."""

        if end <= start:
            raise ValueError("Interval end must be greater than start")
        mapped: List[Tuple[float, float]] = []
        for segment in self.segments:
            overlap_start = max(start, segment.original_start)
            overlap_end = min(end, segment.original_end)
            if overlap_end <= overlap_start:
                continue
            offset_start = overlap_start - segment.original_start
            offset_end = overlap_end - segment.original_start
            mapped.append(
                (
                    segment.derived_start + offset_start,
                    segment.derived_start + offset_end,
                )
            )
        if not mapped:
            raise ValueError("Original interval is outside the mapped timeline")
        return mapped

    def to_dict(self) -> List[dict]:
        return [
            {
                "original_start": round(s.original_start, 6),
                "original_end": round(s.original_end, 6),
                "derived_start": round(s.derived_start, 6),
                "derived_end": round(s.derived_end, 6),
            }
            for s in self.segments
        ]
