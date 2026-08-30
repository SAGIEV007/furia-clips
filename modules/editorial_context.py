"""Deterministic pre-analysis for long political interviews.

This module provides explainable signals before any online model is called. It
never claims speaker identity with certainty; it exposes confidence and keeps
ambiguous turns reviewable.
"""

from __future__ import annotations

import math
import re
from statistics import mean

from .editorial_chapters import build_editorial_chapters


QUESTION_WORDS = {
    "como", "por que", "porque", "porquê", "qual", "quais", "quem", "quando",
    "onde", "o que", "que", "se", "você", "voces", "vocês", "poderia", "acha",
}
RENAN_TERMS = {"renan", "santos", "mbl", "renan santos"}
VISUAL_EVIDENCE_RE = re.compile(
    r"\b(?:gr[aá]fico|pesquisa(?:s)?|ranking|google trends|porcentagem|percentual|dados|imagem(?:s)?|como voc[eê] est[aá] vendo|olha essas imagens|na tela|est[aá] escrito)\b",
    re.IGNORECASE,
)


from modules.safe_types import safe_float, coerce_bool


def _coerce_flag(value: object, default: bool = False) -> bool:
    """Backward-compatible wrapper around safe_types.coerce_bool."""
    return coerce_bool(value, default)


def _requires_visual_evidence(text: str) -> bool:
    """Mark textual references that need a visual check before approval."""
    return bool(VISUAL_EVIDENCE_RE.search(str(text or "")))


def _is_question(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    if "?" in normalized:
        return True
    words = normalized.split()
    if len(words) < 5:
        return False
    first_word = words[0]
    first_phrase = " ".join(words[:2])
    return first_word in QUESTION_WORDS or first_phrase in QUESTION_WORDS


def _speaker_marker(text: str) -> str | None:
    match = re.match(r"^\s*(?:>>\s*)?([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,}(?:\s+[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,})?)\s*:\s*", text)
    return match.group(1) if match else None


def _coerce_confidence(value: object) -> float | None:
    """Normalize diarization confidence without letting NaN/invalid values pass."""
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return max(0.0, min(1.0, parsed))


def _contains_renan(text: str) -> bool:
    normalized = re.sub(r"[^a-záàãâéêíóôõúç ]", " ", text.lower())
    return any(term in normalized for term in RENAN_TERMS)


def analyze_transcript_context(
    transcription: dict,
    focus: str = "auto",
    campaign_hub_snapshot: dict | None = None,
    campaign_hub_account: str | None = None,
) -> dict:
    raw_segments = transcription.get("segments", []) if isinstance(transcription, dict) else []
    segments = []
    for source in raw_segments if isinstance(raw_segments, list) else []:
        if not isinstance(source, dict):
            continue
        try:
            start = float(source.get("start", 0) or 0)
            end = float(source.get("end", start) or start)
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(value) for value in (start, end)) or start < 0 or end <= start:
            continue
        segments.append({**source, "start": start, "end": end})
    # External subtitle providers may return cues out of order. Normalize the
    # temporal sequence before deriving windows, chapters, QA turns and hooks.
    segments.sort(key=lambda item: (item["start"], item["end"]))
    enriched = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        speaker = str(segment.get("speaker", "") or "").strip()
        speaker_confidence = _coerce_confidence(segment.get("speaker_confidence"))
        overlap_suspected = _coerce_flag(segment.get("overlap_suspected", False))
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
    if campaign_hub_snapshot is None:
        try:
            from .campaign_hub import load_snapshot
            campaign_hub_snapshot = load_snapshot()
        except ImportError:
            campaign_hub_snapshot = None
    hook_candidates = detect_hook_candidates(
        enriched,
        snapshot=campaign_hub_snapshot,
        account=campaign_hub_account,
    )
    labeled_speakers = [s for s in enriched if s["speaker_label"]]
    speaker_confidences = [s["speaker_confidence"] for s in labeled_speakers if s["speaker_confidence"] is not None]
    overlap_count = sum(1 for s in enriched if s["overlap_suspected"])
    speaker_coverage = (len(labeled_speakers) / len(enriched)) if enriched else 0.0
    speaker_status = (
        "validated" if labeled_speakers and len(labeled_speakers) == len(enriched)
        else "partial" if labeled_speakers
        else "not_available"
    )
    speaker_detection = {
        "status": speaker_status,
        "labeled_segment_count": len(labeled_speakers),
        "coverage_ratio": round(speaker_coverage, 3),
        "confidence_mean": round(mean(speaker_confidences), 3) if speaker_confidences else None,
        "review_required": speaker_status != "validated",
        "message": (
            "Locutor(es) identificados em todos os segmentos por marcadores/diarização."
            if speaker_status == "validated"
            else "A diarização cobre apenas parte da transcrição; confirme as trocas de locutor no vídeo."
            if speaker_status == "partial"
            else "A transcrição não contém diarização; perguntas e respostas foram inferidas, mas o locutor deve ser confirmado no vídeo."
        ),
    }
    participant_confidence = min(0.95, 0.35 + min(0.45, len(references) * 0.03) + min(0.2, len(questions) * 0.01))
    if not references and not questions:
        participant_confidence = 0.2

    normalized_focus = str(focus or "auto").lower().strip()
    renan_focus = normalized_focus in {"renan", "renan_santos", "renan_santos_politics"}
    if normalized_focus == "auto":
        renan_focus = bool(references)
    focus_key = "renan_santos" if renan_focus else "generic_political"
    focus_label = "Renan Santos" if renan_focus else "participante principal / contexto político"
    if renan_focus and speaker_status != "validated":
        participant_confidence = min(participant_confidence, 0.62 if speaker_status == "partial" else 0.52)

    duration = max((float(s.get("end", 0)) for s in enriched), default=0.0)
    coverage = transcription.get("coverage", {}) if isinstance(transcription, dict) else {}
    coverage_status = str(coverage.get("status", "unknown") or "unknown")
    coverage_review_required = coverage_status in {"partial", "mismatch_suspected", "empty", "unknown"}
    try:
        coverage_segment_count = max(0, int(coverage.get("segment_count", len(enriched)) or 0))
    except (TypeError, ValueError):
        coverage_segment_count = len(enriched)
    transcription_quality = {
        "status": coverage_status,
        "review_required": coverage_review_required,
        "semantic_identity_verified": bool(coverage.get("semantic_identity_verified", False)),
        "last_timestamp": coverage.get("last_timestamp"),
        "end_ratio": coverage.get("end_ratio"),
        "segment_count": coverage_segment_count,
    }
    summary = {
        "duration": round(duration, 3),
        "segment_count": len(enriched),
        "question_count": len(questions),
        "renan_reference_count": len(references),
        "interview_windows": interview_windows,
        "qa_candidates": qa_candidates,
        "editorial_chapters": editorial_chapters,
        "chapter_count": len(editorial_chapters),
        "hook_candidates": hook_candidates,
        "hook_count": len(hook_candidates),
        "chapter_map_version": "v1-temporal-qa",
        "transcription_quality": transcription_quality,
        "focus": focus_key,
        "participant_confidence": round(participant_confidence if renan_focus else min(participant_confidence, 0.55), 3),
        "speaker_detection": speaker_detection,
        "signals": {
            "question_response_structure": bool(qa_candidates),
            "speaker_detection_status": speaker_detection["status"],
            "speaker_markers": sum(1 for s in enriched if s["speaker_marker"]),
            "speaker_labeled_segments": len(labeled_speakers),
            "speaker_confidence_mean": round(mean(speaker_confidences), 3) if speaker_confidences else None,
            "overlap_count": overlap_count,
            "possible_overlap": _possible_overlap(enriched),
            "long_form": duration >= 3600,
            "transcription_coverage_status": coverage_status,
            "transcription_review_required": coverage_review_required,
        },
        "description": _description(duration, len(questions), len(qa_candidates), participant_confidence, focus_label, len(editorial_chapters)) + (
            " A transcrição parcial ou não identificada exige revisão do trecho e pode limitar o contexto."
            if coverage_review_required else ""
        ),
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
        question_start = float(question.get("start", 0) or 0)
        question_speaker = str(question.get("speaker_label", "") or "").strip()
        following = []
        response_indices = []
        speaker_boundary = False
        boundary_basis = "sem_diarização"
        response_speaker = ""
        for offset, candidate in enumerate(segments[index + 1:index + 13], start=index + 1):
            candidate_start = float(candidate.get("start", 0) or 0)
            candidate_speaker = str(candidate.get("speaker_label", "") or "").strip()
            candidate_marker = str(candidate.get("speaker_marker", "") or "").strip()
            candidate_identity = candidate_speaker or candidate_marker
            if candidate.get("is_question") and following and candidate_start - question_start >= 6:
                break
            if response_speaker and candidate_identity and candidate_identity != response_speaker:
                boundary_basis = "segunda_troca_de_locutor"
                break
            following.append(candidate)
            response_indices.append(offset)
            if question_speaker and candidate_identity and candidate_identity != question_speaker:
                speaker_boundary = True
                response_speaker = candidate_identity
                boundary_basis = "mudança_de_locutor"
            elif candidate_marker and candidate_marker != question.get("speaker_marker"):
                speaker_boundary = True
                response_speaker = candidate_marker
                boundary_basis = "marcador_de_locutor"
            if float(candidate.get("end", 0) or 0) - question_start >= 32:
                break
        if not following:
            continue
        end = float(following[-1].get("end", question.get("end", 0)) or question.get("end", 0))
        if end - question_start < 8:
            continue
        renan_signal = any(item["renan_reference"] for item in following)
        overlap = bool(question.get("overlap_suspected")) or any(item.get("overlap_suspected") for item in following)
        confidence = 0.5 + (0.2 if renan_signal else 0) + min(0.16, len(following) * 0.02)
        if speaker_boundary:
            confidence += 0.12
        else:
            # Rhetorical questions inside one speaker's monologue are not
            # reliable interview boundaries. Keep the candidate reviewable,
            # but rank it below a verified interviewer-to-answer transition.
            confidence -= 0.12
        if overlap:
            confidence -= 0.15
        candidates.append({
            "start": round(max(0.0, question_start - 2), 3),
            "end": round(end, 3),
            "question_segment": index,
            "response_segments": response_indices,
            "renan_signal": renan_signal,
            "speaker_boundary": speaker_boundary,
            "boundary_basis": boundary_basis,
            "response_speaker": response_speaker or None,
            "overlap_suspected": overlap,
            "needs_question": True,
            "needs_speaker_review": not speaker_boundary,
            "confidence": round(max(0.2, min(0.98, confidence)), 3),
        })
    return candidates[:50]


def detect_hook_candidates(
    segments: list[dict],
    *,
    snapshot: dict | None = None,
    account: str | None = None,
    energy_profile: list[dict] | None = None,
    limit: int = 12,
) -> list[dict]:
    """Suggest timestamped hook openings without claiming virality.

    Each item is a review lead, not an automatic cut. The score combines a
    deterministic textual hook family, question/contrast/number cues, a nearby
    payoff signal, speaker overlap penalties and an optional Campaign Hub prior
    capped to two points. The returned window is intentionally bounded so an
    editor can verify it against the source video.
    """
    if not segments:
        return []
    try:
        max_items = max(1, min(30, int(limit)))
    except (TypeError, ValueError):
        max_items = 12
    try:
        from .campaign_hub import build_performance_prior, classify_hook_details
    except ImportError:
        build_performance_prior = None
        classify_hook_details = None

    candidates = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "") or "").strip()
        if not text:
            continue
        try:
            start = max(0.0, float(segment.get("start", 0) or 0))
            end = max(start, float(segment.get("end", start) or start))
        except (TypeError, ValueError):
            continue
        details = classify_hook_details(text) if classify_hook_details else {"family": "outro", "evidence": [], "confidence": 0.35}
        family = str(details.get("family", "outro"))
        evidence = list(details.get("evidence", []))[:4]
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        visual_evidence_required = _requires_visual_evidence(text)
        score = 28.0
        reasons = []
        if family != "outro":
            score += 16
            reasons.append(f"abertura classificada como {family}")
        if bool(segment.get("is_question")) or _is_question(text):
            score += 10
            reasons.append("pergunta ou desafio inicial")
        if re.search(r"\b\d+(?:[,.]\d+)?\s*%?\b|\bprimeiro\b|\bsegundo\b|\bmilh", normalized):
            score += 8
            evidence.append("sinal quantitativo")
            reasons.append("contém dado ou ordem concreta")
        if re.search(r"\bmas\b|\bpor[eé]m\b|\benquanto\b|\bdiferente\b|\bna verdade\b", normalized):
            score += 7
            evidence.append("contraste")
            reasons.append("abre uma tensão ou contraste")
        if visual_evidence_required:
            evidence.append("evidência visual citada")
            reasons.append("gráfico, pesquisa ou imagem precisa ser confirmado no vídeo")
        if start <= 35:
            score += 5
            reasons.append("entrada precoce no bloco")
        audio_signal = _audio_signal_for_window(energy_profile, start, end)
        if audio_signal["available"]:
            if audio_signal["contrast"] >= 0.16 or audio_signal["peak"] >= 0.78:
                score += 7
                reasons.append("ênfase de voz/energia detectada")
            elif audio_signal["mean"] <= 0.18:
                score -= 5
                reasons.append("energia baixa; confirmar inteligibilidade")
        setup_cue = bool(re.search(
            r"\b(c[aâ]mera|p[uú]lpito|montou|arrumar|testar|microfone|som|desculpa|risadas|meus queridos|t[aá] na c[aâ]mera)\b",
            normalized,
        ))
        if setup_cue:
            score -= 24
            reasons.append("bastidor ou preparação, não tese final")
        if text[:1].islower() or re.search(r"(?:,|\bpor|\be|\bmas|\bque|\bde)$", normalized):
            score -= 10
            reasons.append("frase começa ou termina fragmentada")
        speaker_label = str(segment.get("speaker_label") or segment.get("speaker") or "").strip()
        raw_speaker_confidence = segment.get("speaker_confidence")
        speaker_confidence = _coerce_confidence(raw_speaker_confidence)
        confidence_invalid = raw_speaker_confidence is not None and speaker_confidence is None
        unknown_labels = {"unknown", "unk", "speaker_unknown", "não identificado", "nao identificado"}
        speaker_known = (
            bool(speaker_label)
            and speaker_label.lower() not in unknown_labels
        ) or bool(segment.get("speaker_marker"))
        speaker_uncertain = (
            not speaker_known
            or confidence_invalid
            or (speaker_confidence is not None and speaker_confidence < 0.65)
        )
        if _coerce_flag(segment.get("overlap_suspected")):
            score -= 14
            reasons.append("sobreposição de falas exige revisão")

        lookahead = []
        for following in segments[index + 1:index + 10]:
            try:
                following_start = float(following.get("start", end) or end)
                following_end = float(following.get("end", following_start) or following_start)
            except (TypeError, ValueError):
                continue
            if following_start - start > 48:
                break
            lookahead.append(following)
            if following_end - start >= 32:
                break
        payoff_text = " ".join(str(item.get("text", "") or "") for item in lookahead).lower()
        payoff_signals = []
        explicit_payoff = bool(re.search(
            r"\b(portanto|por isso|logo|a solu[cç][aã]o|o ponto [eé]|isso significa|na pr[aá]tica|resultado|conclus[aã]o|resposta|basta apenas|essa [eé] a ideia)\b",
            payoff_text,
        ))
        if explicit_payoff:
            payoff_signals.append("marcador explícito de fechamento")
        consequence_question = bool(re.search(
            r"\b(que tipo|qual|como|o que)\b[^?]{0,100}\b(sociedade|pa[ií]s|brasil|futuro|resultado|solu[cç][aã]o|problema|significa|construir|vamos|deve)\b[^?]*\?",
            payoff_text,
        ))
        if consequence_question:
            explicit_payoff = True
            payoff_signals.append("pergunta de consequência")
        repeated_closure = _has_repeated_closure([segment] + lookahead)
        if repeated_closure:
            payoff_signals.append("repetição deliberada da tese no fechamento")
        contentful_lookahead = [item for item in lookahead if len(str(item.get("text", "") or "").split()) >= 5]
        payoff = explicit_payoff or repeated_closure or (
            len(contentful_lookahead) >= 2
            and bool(re.search(r"\b\d+(?:[,.]\d+)?\s*%?\b|\bproposta\w*\b|\btese\b|\bproblema\b", payoff_text))
        )
        if payoff:
            score += 14
            reasons.append("há fechamento ou desenvolvimento próximo")
        else:
            score -= 8
            reasons.append("payoff ainda não confirmado")

        payoff_end = end
        if lookahead:
            try:
                payoff_end = max(end, min(start + 58.0, float(lookahead[-1].get("end", end) or end)))
            except (TypeError, ValueError):
                payoff_end = end
        opening_start = max(0.0, start - 1.5)
        opening_text = text
        if index > 0:
            previous_text = str(segments[index - 1].get("text", "") or "").strip()
            previous_end = re.sub(r"[.!?]+$", "", previous_text.lower()).strip()
            if re.search(r"(?:\bde|\bda|\bdo|\bna|\bno|\bem|\bpor|\bcom|\bque|\bcomo|\be|\bmas)$", previous_end):
                try:
                    opening_start = max(0.0, float(segments[index - 1].get("start", start) or start) - 1.5)
                except (TypeError, ValueError):
                    opening_start = max(0.0, start - 1.5)
                opening_text = f"{previous_text} {text}".strip()
        prior = None
        if build_performance_prior and snapshot:
            prior = build_performance_prior(text, account=account, snapshot=snapshot)
            if prior.get("available"):
                score += max(-2.0, min(2.0, (float(prior.get("observed_signal", 50.0)) - 50.0) / 4.0))
                reasons.append("prior histórico consultado, impacto limitado")
        if end - start < 1.2:
            score -= 7
        score = max(0.0, min(100.0, score))
        candidates.append({
            "segment_index": index,
            "start": round(opening_start, 3),
            "end": round(payoff_end, 3),
            "hook_start": round(start, 3),
            "hook_end": round(min(payoff_end, start + 12.0), 3),
            "family": family,
            "hook_text": opening_text[:240],
            "context_excerpt": " ".join([opening_text] + [str(item.get("text", "") or "").strip() for item in lookahead[:3]])[:420],
            "score": round(score, 1),
            "confidence": round(min(0.98, max(0.2, float(details.get("confidence", 0.35)) * 0.7 + (0.2 if payoff else 0))), 2),
            "evidence": list(dict.fromkeys(evidence))[:6],
            "reason": "; ".join(reasons[:4]),
            "payoff_confirmed": payoff,
            "payoff_signals": payoff_signals[:4],
            "visual_evidence_required": visual_evidence_required,
            "needs_visual_review": _coerce_flag(segment.get("overlap_suspected")) or visual_evidence_required,
            "visual_review_reason": "confirmar gráfico, pesquisa ou imagem mencionada" if visual_evidence_required else "",
            "needs_speaker_review": _coerce_flag(speaker_uncertain),
            "speaker_review_reason": "locutor sem diarização confiável; confirme áudio e vídeo" if speaker_uncertain else "",
            "audio_signal": audio_signal,
            "campaign_hub_prior": prior,
        })

    candidates.sort(key=lambda item: (float(item.get("score", 0)), bool(item.get("payoff_confirmed"))), reverse=True)
    selected = []
    for candidate in candidates:
        if any(
            max(candidate["start"], previous["start"]) < min(candidate["end"], previous["end"]) - 2
            or _hook_text_similarity(candidate.get("hook_text", ""), previous.get("hook_text", "")) >= 0.72
            for previous in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) >= max_items:
            break
    return selected


def _has_repeated_closure(lookahead: list[dict]) -> bool:
    """Detect a short, intentional restatement that can close a thesis."""
    meaningful = [str(item.get("text", "") or "").strip() for item in lookahead if len(str(item.get("text", "") or "").split()) >= 5]
    if len(meaningful) < 2:
        return False
    left = set(re.findall(r"[a-záàãâéêíóôõúç0-9]+", meaningful[-2].lower()))
    right = set(re.findall(r"[a-záàãâéêíóôõúç0-9]+", meaningful[-1].lower()))
    stopwords = {"a", "o", "e", "de", "do", "da", "que", "em", "um", "uma", "para", "por", "com", "na", "no", "nos", "nas", "esse", "essa", "isso"}
    left -= stopwords
    right -= stopwords
    return bool(left and right) and len(left & right) >= 2 and len(left & right) / max(1, len(left | right)) >= 0.42


def _hook_text_similarity(left: str, right: str) -> float:
    """Return a conservative token Jaccard score for repeated hook wording."""
    stopwords = {"a", "o", "e", "de", "do", "da", "que", "em", "um", "uma", "para", "por", "com", "na", "no", "nos", "nas"}
    tokenize = lambda value: {
        token for token in re.findall(r"[a-záàãâéêíóôõúç0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in stopwords
    }
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _audio_signal_for_window(energy_profile: list[dict] | None, start: float, end: float) -> dict:
    """Summarize local RMS energy around a candidate without storing audio."""
    if not isinstance(energy_profile, list) or not energy_profile:
        return {"available": False, "mean": None, "peak": None, "contrast": None, "onset_peak": None, "reaction_peak": None, "review_required": True}
    entries = []
    baseline_entries = []
    midpoint = (start + end) / 2.0
    for item in energy_profile:
        try:
            timestamp = float(item.get("time", 0) or 0)
            normalized = max(0.0, min(1.0, float(item.get("energy_normalized", 0) or 0)))
        except (TypeError, ValueError):
            continue
        if start - 1.5 <= timestamp <= end:
            entries.append(normalized)
        if midpoint - 30 <= timestamp <= midpoint - 5:
            baseline_entries.append(normalized)
    if not entries:
        return {"available": False, "mean": None, "peak": None, "contrast": None, "onset_peak": None, "reaction_peak": None, "review_required": True}
    mean_value = sum(entries) / len(entries)
    baseline = sum(baseline_entries) / len(baseline_entries) if baseline_entries else mean_value
    onset_values = []
    reaction_values = []
    for item in energy_profile:
        try:
            timestamp = float(item.get("time", 0) or 0)
            if start - 1.5 <= timestamp <= end:
                onset_values.append(max(0.0, min(1.0, float(item.get("onset_strength", 0) or 0))))
                reaction_values.append(max(0.0, min(1.0, float(item.get("possible_reaction_signal", 0) or 0))))
        except (TypeError, ValueError):
            continue
    reaction_peak = max(reaction_values, default=0.0)
    return {
        "available": True,
        "mean": round(mean_value, 3),
        "peak": round(max(entries), 3),
        "contrast": round(mean_value - baseline, 3),
        "onset_peak": round(max(onset_values, default=0.0), 3),
        "reaction_peak": round(reaction_peak, 3),
        "review_required": reaction_peak >= 0.58,
    }


def _possible_overlap(segments: list[dict]) -> bool:
    for previous, current in zip(segments, segments[1:]):
        if _coerce_flag(previous.get("overlap_suspected")) or _coerce_flag(current.get("overlap_suspected")):
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
