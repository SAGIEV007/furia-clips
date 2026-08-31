"""Plano de enquadramento explicável para clips.

O módulo não tenta reconhecer pessoas nem substituir análise multimodal. Ele
combina sinais já disponíveis no pipeline e retorna uma decisão conservadora:
reframe somente quando uma única face estável é uma evidência suficiente;
entrevista, split-screen, card, B-roll e institucional preservam a composição
original por padrão.
"""

from __future__ import annotations

from typing import Any, Mapping


SUPPORTED_ASPECTS = {"9:16", "1:1", "16:9"}


_LAYOUT_ALIASES = {
    "single": "single_face",
    "talking_head": "single_face",
    "single_face": "single_face",
    "debate": "multi_speaker",
    "multi_speaker": "multi_speaker",
    "podcast": "multi_speaker",
    "entrevista": "multi_speaker",
    "fullscreen": "text_card",
    "text_card": "text_card",
    "b_roll": "b_roll",
    "text_panel": "text_panel",
    "fake_tweet": "fake_tweet",
    "visual_meme": "visual_meme",
    "institutional": "institutional",
    "campanha": "institutional",
    "unknown": "unknown",
}


def _clamp(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _positive_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _aspect_label(value: Any) -> str:
    label = str(value or "").strip()
    return label if label in SUPPORTED_ASPECTS else "9:16"


def _layout_label(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower().replace("-", "_")
    return _LAYOUT_ALIASES.get(normalized, "unknown")


def _tracking_confidence(assessment: Mapping[str, Any] | None) -> float | None:
    if not assessment:
        return None
    if assessment.get("confident") is True:
        average = _clamp(assessment.get("average_confidence"), 0.0)
        coverage = _clamp(assessment.get("coverage"), 0.0)
        jump = max(0.0, float(assessment.get("largest_jump", 0.0) or 0.0))
        jump_score = max(0.0, 1.0 - min(1.0, jump / 0.30))
        return round(min(1.0, 0.45 * average + 0.35 * coverage + 0.20 * jump_score), 3)
    return 0.0


def _base_result(
    *,
    family: str,
    output_aspect: str,
    reframe_allowed: bool,
    confidence: float,
    review_required: bool,
    reason_code: str,
    reason: str,
    source_aspect: float | None,
    target_aspect: str,
    signals: Mapping[str, Any],
    safe_area: str,
) -> dict[str, Any]:
    return {
        "layout_family": family,
        "output_aspect": output_aspect,
        "target_aspect": target_aspect,
        "reframe_allowed": reframe_allowed,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "review_required": review_required,
        "reason_code": reason_code,
        "reason": reason,
        "source_aspect": round(source_aspect, 4) if source_aspect else None,
        "safe_area": safe_area,
        "signals": dict(signals),
    }


def plan_layout(
    *,
    original_aspect: float | None = None,
    detected_layout: str | None = None,
    face_count: int | None = None,
    split_screen: bool = False,
    has_text_card: bool = False,
    has_b_roll: bool = False,
    institutional: bool = False,
    dialogue_density: float | None = None,
    tracking_assessment: Mapping[str, Any] | None = None,
    speaker_confidence: float | None = None,
    active_speaker_confidence: float | None = None,
    visual_format: str | None = None,
    text_panel: bool = False,
    fake_tweet: bool = False,
    visual_meme: bool = False,
    external_evidence: bool = False,
    target_aspect: str = "9:16",
    explicit_original: bool = False,
) -> dict[str, Any]:
    """Return a conservative, serializable layout decision for one clip.

    ``tracking_assessment`` is the object returned by
    :meth:`FaceTracker.assess_segment_tracking`. A decision that preserves the
    original composition is still a successful decision; it is not a failure
    of the planner.
    """

    target = _aspect_label(target_aspect)
    family_hint = _layout_label(detected_layout)
    face_total = _positive_int(face_count)
    speaker_score = _clamp(active_speaker_confidence)
    if speaker_score is None:
        speaker_score = _clamp(speaker_confidence)
    tracking_score = _tracking_confidence(tracking_assessment)
    assessment_confident = bool(tracking_assessment and tracking_assessment.get("confident") is True)
    multiple_samples = _positive_int((tracking_assessment or {}).get("multiple_face_samples"))
    multi_face_ratio = _clamp((tracking_assessment or {}).get("multi_face_ratio"), 0.0)
    # A correção (31/08): usar a PROPORÇÃO de frames com múltiplas faces,
    # não a contagem absoluta. Um frame isolado de plateia ao fundo
    # não deve condenar um trecho inteiro de orador único.
    # O critério real está no assess_segment_tracking (max_multi_face_ratio=0.30).
    if face_total < 2 and multiple_samples > 0 and multi_face_ratio > 0.30:
        face_total = 2

    signals = {
        "detected_layout": family_hint,
        "face_count": face_total,
        "split_screen": bool(split_screen),
        "has_text_card": bool(has_text_card),
        "has_b_roll": bool(has_b_roll),
        "institutional": bool(institutional),
        "visual_format": _layout_label(visual_format),
        "text_panel": bool(text_panel),
        "fake_tweet": bool(fake_tweet),
        "visual_meme": bool(visual_meme),
        "external_evidence": bool(external_evidence),
        "dialogue_density": _clamp(dialogue_density),
        "tracking_confidence": tracking_score,
        "speaker_confidence": speaker_score,
        "tracking_confident": assessment_confident,
    }

    if explicit_original or target == "16:9":
        return _base_result(
            family=family_hint if family_hint != "unknown" else "original",
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.96 if explicit_original else 0.91,
            review_required=False,
            reason_code="original_requested",
            reason="A proporção original foi solicitada ou já corresponde ao destino; nenhum crop será aplicado.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="full_frame",
        )

    visual_hint = _layout_label(visual_format)
    if (
        text_panel or fake_tweet or visual_meme or external_evidence
        or visual_hint in {"text_panel", "fake_tweet", "visual_meme"}
    ):
        if fake_tweet or visual_hint == "fake_tweet":
            family = "fake_tweet"
        elif visual_meme or visual_hint == "visual_meme":
            family = "visual_meme"
        elif text_panel or visual_hint == "text_panel":
            family = "text_panel"
        else:
            family = "visual_composition"
        safe_area = "text_and_edges" if text_panel or visual_hint == "text_panel" else "full_frame"
        return _base_result(
            family=family,
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.90,
            review_required=True,
            reason_code="visual_composition_preserve",
            reason="Painel, post social, arte composta ou evidência visual ocupa parte essencial do argumento; preserve o quadro inteiro antes de qualquer reframe.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area=safe_area,
        )

    if institutional or family_hint == "institutional":
        return _base_result(
            family="institutional",
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.90,
            review_required=True,
            reason_code="institutional_preserve",
            reason="Peça institucional depende de cartelas, margens, montagem ou assinatura; preserve o quadro e revise a mensagem visual.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="text_and_edges",
        )

    if split_screen or family_hint == "multi_speaker" or face_total >= 2:
        return _base_result(
            family="split_screen" if split_screen else "multi_speaker",
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.92,
            review_required=True,
            reason_code="multiple_subjects",
            reason="Há mais de um sujeito ou uma composição dividida; o crop de uma face poderia remover a pergunta, a reação ou a evidência.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="multi_subject",
        )

    if has_text_card or family_hint == "text_card":
        return _base_result(
            family="text_card",
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.88,
            review_required=True,
            reason_code="text_card_protect",
            reason="Texto ou card ocupa parte relevante do quadro; preserve bordas e área segura para não cortar informação.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="text_and_edges",
        )

    if has_b_roll or family_hint == "b_roll":
        return _base_result(
            family="b_roll",
            output_aspect="original",
            reframe_allowed=False,
            confidence=0.84,
            review_required=True,
            reason_code="b_roll_preserve",
            reason="B-roll ou evidência externa pode ser parte do argumento; preserve a composição até validar o retorno ao locutor.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="full_frame",
        )

    if family_hint == "single_face" and assessment_confident:
        confidence = tracking_score if tracking_score is not None else 0.75
        if speaker_score is not None:
            confidence = min(confidence, max(0.0, speaker_score))
        return _base_result(
            family="single_face",
            output_aspect=target,
            reframe_allowed=True,
            confidence=confidence,
            review_required=confidence < 0.75,
            reason_code="single_face_stable",
            reason="Uma única face tem cobertura, confiança e estabilidade suficientes para reenquadramento conservador.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="face_center",
        )

    if assessment_confident and face_total <= 1:
        confidence = tracking_score if tracking_score is not None else 0.70
        return _base_result(
            family="single_face",
            output_aspect=target,
            reframe_allowed=True,
            confidence=confidence,
            review_required=confidence < 0.75,
            reason_code="single_face_inferred",
            reason="O tracking indica uma face estável, embora o layout de origem não tenha sido rotulado explicitamente.",
            source_aspect=original_aspect,
            target_aspect=target,
            signals=signals,
            safe_area="face_center",
        )

    return _base_result(
        family="unknown",
        output_aspect="original",
        reframe_allowed=False,
        confidence=0.42,
        review_required=True,
        reason_code="insufficient_evidence",
        reason="Não há evidência visual suficiente de um locutor único e estável; preserve a proporção original e revise o enquadramento.",
        source_aspect=original_aspect,
        target_aspect=target,
        signals=signals,
        safe_area="full_frame",
    )


__all__ = ["SUPPORTED_ASPECTS", "plan_layout"]