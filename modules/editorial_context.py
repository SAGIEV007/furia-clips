"""Deterministic pre-analysis for long political interviews.

This module provides explainable signals before any online model is called. It
never claims speaker identity with certainty; it exposes confidence and keeps
ambiguous turns reviewable.
"""

from __future__ import annotations

import re
from statistics import mean


QUESTION_WORDS = {
    "como", "por que", "porque", "porquê", "qual", "quais", "quem", "quando",
    "onde", "o que", "que", "se", "você", "voces", "vocês", "poderia", "acha",
}
RENAN_TERMS = {"renan", "santos", "mbl", "renan santos"}


def _is_question(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    if "?" in normalized:
        return True
    first = normalized.split(" ", 2)
    return bool(first and first[0] in QUESTION_WORDS and len(normalized.split()) >= 5)


def _speaker_marker(text: str) -> str | None:
    match = re.match(r"^\s*(?:>>\s*)?([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,}(?:\s+[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,})?)\s*:\s*", text)
    return match.group(1) if match else None


def _contains_renan(text: str) -> bool:
    normalized = re.sub(r"[^a-záàãâéêíóôõúç ]", " ", text.lower())
    return any(term in normalized for term in RENAN_TERMS)


def analyze_transcript_context(transcription: dict) -> dict:
    segments = transcription.get("segments", []) if isinstance(transcription, dict) else []
    enriched = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        enriched.append({
            **segment,
            "is_question": _is_question(text),
            "speaker_marker": _speaker_marker(text),
            "renan_reference": _contains_renan(text),
        })

    questions = [s for s in enriched if s["is_question"]]
    references = [s for s in enriched if s["renan_reference"]]
    interview_windows = _build_interview_windows(enriched)
    qa_candidates = _build_qa_candidates(enriched)
    participant_confidence = min(0.95, 0.35 + min(0.45, len(references) * 0.03) + min(0.2, len(questions) * 0.01))
    if not references and not questions:
        participant_confidence = 0.2

    duration = max((float(s.get("end", 0)) for s in enriched), default=0.0)
    summary = {
        "duration": round(duration, 3),
        "segment_count": len(enriched),
        "question_count": len(questions),
        "renan_reference_count": len(references),
        "interview_windows": interview_windows,
        "qa_candidates": qa_candidates,
        "focus": "renan_santos",
        "participant_confidence": round(participant_confidence, 3),
        "signals": {
            "question_response_structure": bool(qa_candidates),
            "speaker_markers": sum(1 for s in enriched if s["speaker_marker"]),
            "possible_overlap": _possible_overlap(enriched),
            "long_form": duration >= 3600,
        },
        "description": _description(duration, len(questions), len(qa_candidates), participant_confidence),
    }
    return summary


def _build_interview_windows(segments: list[dict]) -> list[dict]:
    if not segments:
        return []
    windows = []
    window_start = None
    window_end = None
    score = 0
    for segment in segments:
        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))
        evidence = int(segment.get("is_question")) + int(segment.get("renan_reference"))
        active = evidence > 0
        if active and window_start is None:
            window_start = max(0.0, start - 30.0)
            window_end = end
            score = evidence
        elif active and window_start is not None and start - (window_end or start) <= 180:
            window_end = end
            score += evidence
        elif window_start is not None:
            if (window_end or window_start) - window_start >= 30:
                windows.append({"start": round(window_start, 3), "end": round(window_end or window_start, 3), "evidence": score})
            window_start = max(0.0, start - 30.0) if active else None
            window_end = end if active else None
            score = evidence
    if window_start is not None and window_end is not None and window_end - window_start >= 30:
        windows.append({"start": round(window_start, 3), "end": round(window_end, 3), "evidence": score})
    return _merge_windows(windows)


def _merge_windows(windows: list[dict]) -> list[dict]:
    merged = []
    for window in windows:
        if merged and window["start"] <= merged[-1]["end"] + 60:
            merged[-1]["end"] = max(merged[-1]["end"], window["end"])
            merged[-1]["evidence"] += window["evidence"]
        else:
            merged.append(window.copy())
    return merged[:20]


def _build_qa_candidates(segments: list[dict]) -> list[dict]:
    candidates = []
    for index, question in enumerate(segments):
        if not question["is_question"]:
            continue
        following = []
        for candidate in segments[index + 1:index + 12]:
            following.append(candidate)
            if float(candidate.get("end", 0)) - float(question.get("start", 0)) >= 20:
                break
        if not following:
            continue
        end = float(following[-1].get("end", question.get("end", 0)))
        if end - float(question.get("start", 0)) < 8:
            continue
        renan_signal = any(item["renan_reference"] for item in following)
        candidates.append({
            "start": round(max(0.0, float(question.get("start", 0)) - 2), 3),
            "end": round(end, 3),
            "question_segment": index,
            "response_segments": [segments.index(item) for item in following],
            "renan_signal": renan_signal,
            "needs_question": True,
            "confidence": round(0.55 + (0.2 if renan_signal else 0) + min(0.2, len(following) * 0.015), 3),
        })
    return candidates[:50]


def _possible_overlap(segments: list[dict]) -> bool:
    for previous, current in zip(segments, segments[1:]):
        if float(current.get("start", 0)) < float(previous.get("end", 0)) - 0.1:
            return True
    return False


def _description(duration: float, question_count: int, qa_count: int, confidence: float) -> str:
    hours = duration / 3600 if duration else 0
    size = "vídeo longo" if hours >= 1 else "vídeo curto/médio"
    return (
        f"Pré-análise: {size} com {question_count} perguntas detectadas e {qa_count} "
        f"candidatos pergunta–resposta. O foco editorial configurado é Renan Santos, "
        f"com confiança inicial de {confidence:.0%}; confirme casos ambíguos na revisão."
    )
