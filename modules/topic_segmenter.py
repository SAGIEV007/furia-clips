"""Split a long transcript into coherent thematic units, from the text alone.

The Acervo turns a source into QA-gated blocks, and everything outside a block is
non-content. Furia consumed those blocks but could not produce them, so a source
the Acervo never labelled arrived with no structure at all.

The first attempt here tried to recognise non-content by vocabulary — greetings,
requests for likes, production chatter. Measured against the regions the Acervo
labelled on two real sources it recovered 3.4% of them, because the labels are
judgements about whether a stretch sustains an argument, not about which words it
contains. "Casual banter with an analogy about Pokémon" has no keyword.

What follows treats the real problem: where does one subject end and the next
begin. Boundaries are found by lexical cohesion between neighbouring windows of
sentences — a valley in cohesion is a change of subject — and each resulting
segment is then judged on whether it develops a subject at all.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from .non_content_detector import score_segment

_WORD = re.compile(r"[0-9a-zà-ü]+")

# Function words carry no topic. Keeping them would make every pair of windows
# look similar, flattening the cohesion curve that boundaries are read from.
_STOPWORDS = {
    "a", "à", "às", "ao", "aos", "aquele", "aquela", "aqui", "as", "até", "com", "como",
    "da", "das", "de", "dela", "dele", "deles", "do", "dos", "e", "é", "ela", "elas",
    "ele", "eles", "em", "entre", "era", "essa", "esse", "esta", "está", "estamos",
    "estão", "este", "eu", "foi", "for", "isso", "isto", "já", "lá", "mais", "mas",
    "me", "mesmo", "meu", "muito", "na", "não", "nas", "nem", "no", "nos", "nós",
    "num", "numa", "o", "os", "ou", "para", "pela", "pelo", "por", "porque", "que",
    "quando", "se", "sem", "ser", "seu", "sua", "são", "só", "também", "te", "tem",
    "ter", "teu", "um", "uma", "vai", "vamos", "você", "vocês", "aí", "então", "né",
    "assim", "coisa", "gente", "cara", "tá", "pra", "pro", "lo", "la", "das", "dessa",
}


def _tokens(text: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower()
    return [word for word in _WORD.findall(lowered) if len(word) > 2 and word not in _STOPWORDS]


def _cosine(left: dict[str, int], right: dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    dot = sum(left[word] * right[word] for word in shared)
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def _counts(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return counts


def cohesion_curve(segments: list[dict[str, Any]], window: int) -> list[float]:
    """Lexical similarity across each gap between sentences.

    Each gap is scored by comparing the vocabulary of the ``window`` sentences
    before it with the ``window`` sentences after it. A low value means the two
    sides talk about different things.
    """
    words = [_tokens(item.get("text")) for item in segments]
    curve = []
    for gap in range(1, len(segments)):
        before = _counts([word for chunk in words[max(0, gap - window):gap] for word in chunk])
        after = _counts([word for chunk in words[gap:gap + window] for word in chunk])
        curve.append(_cosine(before, after))
    return curve


def _boundaries(curve: list[float], min_gap: int) -> list[int]:
    """Gaps that sit in a cohesion valley deeper than the local average."""
    if not curve:
        return []
    mean = sum(curve) / len(curve)
    deviation = math.sqrt(sum((value - mean) ** 2 for value in curve) / len(curve))
    # A boundary must be a local minimum and clearly below the average cohesion,
    # otherwise ordinary variation inside one subject would cut it in pieces.
    # Calibrated against 27 Acervo blocks on a 98-minute source: a shallower
    # threshold fragmented one subject into many, a deeper one collapsed the
    # whole transcript into a single unit.
    threshold = mean - deviation
    candidates = []
    for index in range(1, len(curve) - 1):
        if curve[index] <= threshold and curve[index] <= curve[index - 1] and curve[index] <= curve[index + 1]:
            candidates.append(index)

    chosen: list[int] = []
    for index in sorted(candidates, key=lambda position: curve[position]):
        if all(abs(index - taken) >= min_gap for taken in chosen):
            chosen.append(index)
    return sorted(chosen)


def segment_transcript(
    segments: list[dict[str, Any]],
    *,
    window: int = 6,
    min_sentences: int = 32,
    min_duration_s: float = 15.0,
    max_duration_s: float = 720.0,
) -> list[dict[str, Any]]:
    """Split the transcript into thematic units and judge each one.

    The duration bounds mirror what the Acervo produces: its blocks run from 15s
    to about 12 minutes. Each unit is returned with the evidence behind the
    verdict, never as a bare accept or reject.
    """
    usable = [
        item for item in segments or []
        if str(item.get("text") or "").strip()
        and float(item.get("end", 0) or 0) > float(item.get("start", 0) or 0)
    ]
    if len(usable) < min_sentences * 2:
        return []

    cuts = _boundaries(cohesion_curve(usable, window), min_sentences)
    edges = [0, *[cut + 1 for cut in cuts], len(usable)]

    units: list[dict[str, Any]] = []
    for start_index, end_index in zip(edges, edges[1:]):
        group = usable[start_index:end_index]
        if not group:
            continue
        start = float(group[0].get("start", 0) or 0)
        end = float(group[-1].get("end", 0) or 0)
        duration = end - start
        if duration < min_duration_s:
            continue
        text = " ".join(str(item.get("text") or "") for item in group)
        words = _tokens(text)
        verdict = score_segment(text, words_per_second=len(_WORD.findall(text.lower())) / max(0.001, duration))
        # Vocabulary that keeps returning is a subject being developed; a stretch
        # where almost nothing repeats is a sequence of unrelated remarks.
        recurrence = 1.0 - (len(set(words)) / len(words)) if words else 0.0
        # A unit long enough to develop something, whose vocabulary returns often
        # enough to be about a subject, and that the cue scorer does not read as
        # broadcast filler.
        units.append({
            "start_s": round(start, 3),
            "end_s": round(min(end, start + max_duration_s), 3),
            "duration_s": round(min(duration, max_duration_s), 3),
            "sentence_count": len(group),
            "start_sentence_index": start_index,
            "end_sentence_index": end_index - 1,
            "topic_terms": [word for word, _ in sorted(_counts(words).items(), key=lambda pair: -pair[1])[:8]],
            "recurrence": round(recurrence, 3),
            "carries_subject": bool(recurrence >= 0.2 and len(words) >= 60 and not verdict["non_content"]),
            "non_content_cues": verdict["cues"],
            "provenance": "furia_topic_segmenter",
        })
    return units
