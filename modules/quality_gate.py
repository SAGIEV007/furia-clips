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
        if not flags.get("context_complete"):
            reasons.append("contexto_incompleto")
        if not flags.get("payoff_complete"):
            reasons.append("payoff_incompleto")
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
