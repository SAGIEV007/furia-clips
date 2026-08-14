"""Deterministic pre-analysis for long political interviews.

This module provides explainable signals before any online model is called. It
never claims speaker identity with certainty; it exposes confidence and keeps
ambiguous turns reviewable.
"""

from __future__ import annotations

import re
from statistics import mean

from .editorial_chapters import build_editorial_chapters


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


def analyze_transcript_context(transcription: dict, focus: str = "auto") -> dict:
    segments = transcription.get("segments", []) if isinstance(transcription, dict) else []
    enriched = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        speaker = str(segment.get("speaker", "") or "").strip()
        raw_confidence = segment.get("speaker_confidence")
        try:
            speaker_confidence = max(0.0, min(1.0, float(raw_confidence))) if raw_confidence is not None else None
        except (TypeError, ValueError):
            speaker_confidence = None
        overlap_suspected = bool(segment.get("overlap_suspected", False))
        enriched.append({
            **segment,
            "is_question": _is_question(text),
            "speaker_marker": _speaker_marker(text),
            "speaker_label": speaker or None,
            "speaker_confidence": speaker_confidence,
            "overlap_suspected": overlap_suspected,
            "renan_reference": _contains_renan(text),
        })

    questions = [s for s in enriched if s["is_question"]]
    references = [s for s in enriched if s["renan_reference"]]
    interview_windows = _build_interview_windows(enriched)
    qa_candidates = _build_qa_candidates(enriched)
    editorial_chapters = build_editorial_chapters(enriched, qa_candidates)
    labeled_speakers = [s for s in enriched if s["speaker_label"]]
    speaker_confidences = [s["speaker_confidence"] for s in labeled_speakers if s["speaker_confidence"] is not None]
    overlap_count = sum(1 for s in enriched if s["overlap_suspected"])
    participant_confidence = min(0.95, 0.35 + min(0.45, len(references) * 0.03) + min(0.2, len(questions) * 0.01))
    if not references and not questions:
        participant_confidence = 0.2

    normalized_focus = str(focus or "auto").lower().strip()
    renan_focus = normalized_focus in {"renan", "renan_santos", "renan_santos_politics"}
    if normalized_focus == "auto":
        renan_focus = bool(references)
    focus_key = "renan_santos" if renan_focus else "generic_political"
    focus_label = "Renan Santos" if renan_focus else "participante principal / contexto político"

    duration = max((float(s.get("end", 0)) for s in enriched), default=0.0)
    summary = {
        "duration": round(duration, 3),
        "segment_count": len(enriched),
        "question_count": len(questions),
        "renan_reference_count": len(references),
        "interview_windows": interview_windows,
        "qa_candidates": qa_candidates,
        "editorial_chapters": editorial_chapters,
        "chapter_count": len(editorial_chapters),
        "chapter_map_version": "v1-temporal-qa",
        "focus": focus_key,
        "participant_confidence": round(participant_confidence if renan_focus else min(participant_confidence, 0.55), 3),
        "signals": {
            "question_response_structure": bool(qa_candidates),
            "speaker_markers": sum(1 for s in enriched if s["speaker_marker"]),
            "speaker_labeled_segments": len(labeled_speakers),
            "speaker_confidence_mean": round(mean(speaker_confidences), 3) if speaker_confidences else None,
            "overlap_count": overlap_count,
            "possible_overlap": _possible_overlap(enriched),
            "long_form": duration >= 3600,
        },
        "description": _description(duration, len(questions), len(qa_candidates), participant_confidence, focus_label, len(editorial_chapters)),
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
        if bool(previous.get("overlap_suspected")) or bool(current.get("overlap_suspected")):
            return True
        if float(current.get("start", 0)) < float(previous.get("end", 0)) - 0.1:
            return True
    return False


def _description(duration: float, question_count: int, qa_count: int, confidence: float, focus_label: str, chapter_count: int = 0) -> str:
    hours = duration / 3600 if duration else 0
    size = "vídeo longo" if hours >= 1 else "vídeo curto/médio"
    return (
        f"Pré-análise: {size} com {question_count} perguntas detectadas e {qa_count} "
        f"candidatos pergunta–resposta e {chapter_count} capítulos editoriais. O foco editorial é {focus_label}, "
        f"com confiança inicial de {confidence:.0%}; confirme casos ambíguos na revisão."
    )
