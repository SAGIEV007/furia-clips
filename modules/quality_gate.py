"""Quality gate: rejects clips that fail hard editorial checks.

This is a SEPARATE gate from the scoring system. A clip can score 80/100
and still be rejected here if:
  - it opens mid-sentence or depends on prior context
  - it ends fragmented, on a cliffhanger, or before the answer
  - it is a duplicate of a higher-scoring clip
  - it lacks context or payoff (both flags must be True)

Rejected clips are logged with reasons for calibration review.
"""

from __future__ import annotations

from typing import Any

from difflib import SequenceMatcher

from .fronteira_assunto import abre_dependente, fim_fragmentado


# Minimum viral score to survive the gate. Calibrated from editorial
# baseline: A=80, B=25, C=0 weighted across 4 axes. A clip that passes
# all editorial flags should score at least 45/100. Lower = structural
# failure, not just weak content.
_MIN_VIRAL_SCORE = 45

# Maximum overlap ratio (0-1) before the shorter/lower-scored clip is
# considered a duplicate. 0.60 = 60% shared material.
_MAX_OVERLAP_RATIO = 0.60

# Minimum duration in seconds for a clip to be considered a real cut
# rather than a truncation artifact.
_MIN_DURATION_S = 5.0


def _overlaps(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Return the overlap ratio between two clips (0 = disjoint, 1 = identical)."""
    a_start = float(a.get("start", 0) or 0)
    a_end = float(a.get("end", 0) or 0)
    b_start = float(b.get("start", 0) or 0)
    b_end = float(b.get("end", 0) or 0)
    overlap = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    a_dur = max(a_end - a_start, 0.001)
    return overlap / a_dur


def _text_similarity(a: str, b: str) -> float:
    """Return 0-1 similarity between two text strings."""
    if not a or not b:
        return 0.0
    a_clean = " ".join(str(a).split())
    b_clean = " ".join(str(b).split())
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _is_reporter_question(text: str) -> bool:
    """Detect if the clip starts with or contains a reporter question that
    should not be the opening of a clip."""
    if not text:
        return False
    lower = text.lower()
    # Reporter question markers
    reporter_markers = [
        "o senhor acha",
        "você acha",
        "como o senhor",
        "como você",
        "o que o senhor",
        "o que você",
        "por que o senhor",
        "por que você",
        "quando o senhor",
        "quando você",
        "onde o senhor",
        "onde você",
        "o presidente da república tem que ser",
        "o presidente tem que ser",
        "se você não acha",
        "seriam 30 mil pessoas",
        "chamava muito a atenção",
    ]
    for marker in reporter_markers:
        if marker in lower:
            return True
    return False


def _ends_on_question(text: str) -> bool:
    """Detect if the clip ends on a reporter question or incomplete thought."""
    if not text:
        return False
    stripped = text.strip()
    # Ends with question mark
    if stripped.endswith("?"):
        return True
    # Ends with incomplete question markers
    incomplete_markers = [
        "o senhor acha",
        "você acha",
        "como o senhor",
        "como você",
        "o que o senhor",
        "o que você",
        "por que o senhor",
        "por que você",
    ]
    for marker in incomplete_markers:
        if stripped.lower().endswith(marker):
            return True
    return False


def _starts_with_reporter_question(text: str) -> bool:
    """Check if the clip text STARTS with a reporter question marker.

    This is different from _is_reporter_question which checks anywhere in text.
    The boundary repair should have moved the start past the question.
    If the text still starts with a reporter question, the boundary repair failed.
    """
    if not text:
        return False
    stripped = text.lstrip().lower()
    # Reporter question markers at the very start
    reporter_starters = [
        "candidato",
        "o senhor",
        "você ",
        "como o senhor",
        "como você",
        "o que o senhor",
        "o que você",
        "por que o senhor",
        "por que você",
        "quando o senhor",
        "quando você",
        "onde o senhor",
        "onde você",
        "o presidente da república",
        "o presidente tem que ser",
        "seriam 30 mil pessoas",
        "chamava muito a atenção",
    ]
    for marker in reporter_starters:
        if stripped.startswith(marker):
            return True
    return False


def _has_minimum_context(text: str, min_words: int = 6) -> bool:
    """Check if the clip has at least min_words of context before the main hook."""
    if not text:
        return False
    words = text.split()
    return len(words) >= min_words


def _has_substantive_answer(text: str) -> bool:
    """Check if the clip contains a substantive answer after a question.

    A valid Q&A clip starts with the reporter's question AND includes
    Renan's substantive answer. We check for first-person/assertion markers
    after the first question mark.
    """
    if not text:
        return False
    first_qmark = text.find("?")
    if first_qmark < 0:
        return False
    after_question = text[first_qmark + 1:].strip()
    if len(after_question) <= 30:
        return False
    answer_markers = [
        "eu ", "nós ", "minha ", "minha opinião", "eu acho", "eu vou",
        "vamos ", "é ", "não ", "sim ", "acho que", "acredito",
        "defendo", "proponho", "entendo", "pensamento"
    ]
    after_lower = after_question.lower()
    return any(m in after_lower for m in answer_markers)


def apply_quality_gate(clips: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter clips through hard editorial gates.

    Returns (accepted, rejected) where each list contains clip dicts.
    Rejected clips carry a ``rejection_reasons`` list for calibration review.
    """
    if not clips:
        return [], []

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    # Sort by score descending so the best clip wins duplicate conflicts.
    ranked = sorted(clips, key=lambda c: float(c.get("viral_score", 0) or 0), reverse=True)

    for clip in ranked:
        reasons: list[str] = []
        text = str(clip.get("text") or "")
        start = float(clip.get("start", 0) or 0)
        end = float(clip.get("end", 0) or 0)
        duration = max(0.0, end - start)
        score = float(clip.get("viral_score", 0) or 0)

        # Gate 1: minimum duration (truncation artifact filter).
        if duration < _MIN_DURATION_S:
            reasons.append(f"duracao_abaixo_de_{_MIN_DURATION_S:.0f}s")

        # Gate 2: minimum viral score.
        if score < _MIN_VIRAL_SCORE:
            reasons.append(f"viral_score_{score:.0f}_abaixo_de_{_MIN_VIRAL_SCORE}")

        # Gate 3: hard editorial flags.
        flags = clip if isinstance(clip, dict) else {}
        if flags.get("starts_mid_sentence"):
            reasons.append("abre_no_meio_da_frase")
        if flags.get("starts_with_context_reference"):
            reasons.append("abre_com_referencia_orfã")
        if flags.get("opening_dependent") or abre_dependente(text):
            reasons.append("abertura_dependente")
        if flags.get("ending_fragmented") or fim_fragmentado(text):
            reasons.append("fim_fragmentado")
        if flags.get("question_detected") and not flags.get("qa_bridge") and not flags.get("qa_bridge_local"):
            reasons.append("pergunta_sem_resposta")
        if not flags.get("context_complete", True):
            reasons.append("contexto_incompleto")
        if not flags.get("payoff_complete", True):
            reasons.append("payoff_incompleto")

        # Gate 3b: clip STARTS with reporter question (boundary repair failed)
        # The boundary repair (_align_to_interview_turns, _open_where_the_thought_begins)
        # should have moved the start past the reporter's question to the guest's answer.
        # If the clip still starts with a reporter question marker, the repair failed.
        if _starts_with_reporter_question(text) and not _has_substantive_answer(text):
            reasons.append("abre_com_pergunta_do_reporter")

        # Gate 3c: clip should not end on a question
        if _ends_on_question(text):
            reasons.append("termina_na_pergunta")

        # Gate 3d: minimum context check
        if not _has_minimum_context(text, min_words=6):
            reasons.append("contexto_insuficiente")

        if flags.get("overlap_suspected"):
            reasons.append("tempo_ambiguo")
        if flags.get("contains_broadcast_break"):
            reasons.append("atravessa_intervalo")

        # Gate 4: duplicate / near-duplicate against already-accepted clips.
        duplicate_of = None
        for existing in accepted:
            overlap = _overlaps(clip, existing)
            sim = _text_similarity(text, str(existing.get("text") or ""))
            if overlap >= _MAX_OVERLAP_RATIO or (sim >= 0.80 and overlap >= 0.40):
                duplicate_of = existing
                break
        if duplicate_of:
            existing_score = float(duplicate_of.get("viral_score", 0) or 0)
            if score <= existing_score:
                reasons.append(f"duplicata_de_score_{existing_score:.0f}")
            else:
                # This clip is better — replace the existing one.
                accepted.remove(duplicate_of)
                rejected.append({**duplicate_of, "rejection_reasons": ["substituido_por_corte_maior"]})

        if reasons:
            rejected.append({**clip, "rejection_reasons": reasons})
        else:
            accepted.append(clip)

    return accepted, rejected