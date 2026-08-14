"""Deterministic visual-format classification for editorial review.

The classifier is intentionally conservative. It prefers explicit metadata from
analysis over lexical guesses and returns ``desconhecido`` when the available
signals do not justify a format label. A format label is a routing and review
signal; it is not a claim about virality or truth.
"""

from __future__ import annotations

from typing import Any


KNOWN_FORMATS = {
    "talking_head",
    "selfie_proximo",
    "entrevista",
    "podcast",
    "react",
    "split_screen",
    "evidencia_externa",
    "b_roll_argumentativo",
    "palco",
    "institucional",
    "campanha",
    "testemunhal",
    "unboxing",
    "humor_bastidor",
    "desconhecido",
}

_PRESERVE_COMPOSITION = {
    "entrevista",
    "podcast",
    "react",
    "split_screen",
    "evidencia_externa",
    "b_roll_argumentativo",
    "palco",
    "institucional",
    "campanha",
    "testemunhal",
    "unboxing",
    "desconhecido",
}

_TRUE_VALUES = {True, 1, "1", "true", "yes", "sim", "y"}


def classify_editorial_format(clip: dict[str, Any] | None, text: str = "") -> dict[str, Any]:
    """Return a conservative format profile for one candidate clip.

    Explicit fields are preferred in this order: ``visual_format``,
    ``format_family``, ``layout_family`` and ``source_family``. When no explicit
    value exists, only a small set of structured booleans is used. Text is used
    for tie-breaking between an explicitly detected split-screen and a likely
    reaction/interview, never to invent an audiovisual format on its own.
    """
    data = clip or {}
    explicit = _first_known(data, ("visual_format", "format_family", "layout_family", "source_family"))
    if explicit:
        return _profile(explicit, 0.96, "formato declarado pela análise")

    normalized = _normalize(text)
    if _truthy(data.get("split_screen")) or _truthy(data.get("has_split_screen")):
        if _has_any(normalized, ("reag", "responde", "comentando", "noticia", "cctv")):
            return _profile("react", 0.86, "split-screen com sinais de reação ou evidência externa")
        if "?" in str(text) or _has_any(normalized, ("entrevista", "pergunta", "resposta", "podcast")):
            return _profile("entrevista", 0.82, "split-screen com sinais de pergunta e resposta")
        return _profile("split_screen", 0.78, "split-screen detectado sem família semântica suficiente")

    if _truthy(data.get("external_evidence")) or _truthy(data.get("has_external_evidence")):
        return _profile("evidencia_externa", 0.84, "evidência visual externa declarada pela análise")
    if _truthy(data.get("institutional")) or _truthy(data.get("is_institutional")):
        return _profile("institucional", 0.84, "peça institucional declarada pela análise")
    if _truthy(data.get("campaign")) or _truthy(data.get("is_campaign")):
        return _profile("campanha", 0.84, "peça de campanha declarada pela análise")
    if _truthy(data.get("interview")) or _truthy(data.get("is_interview")):
        return _profile("entrevista", 0.84, "entrevista declarada pela análise")
    if _truthy(data.get("podcast")) or _truthy(data.get("is_podcast")):
        return _profile("podcast", 0.84, "podcast declarado pela análise")
    if _truthy(data.get("stage")) or _truthy(data.get("is_stage")):
        return _profile("palco", 0.80, "palco declarado pela análise")
    if _truthy(data.get("testimony")) or _truthy(data.get("testimonial")):
        return _profile("testemunhal", 0.80, "testemunhal declarado pela análise")

    face_count = _number(data.get("face_count"))
    speaker_confidence = _number(data.get("speaker_confidence"))
    if face_count is not None and face_count > 1:
        return _profile("entrevista", 0.70, "mais de uma face detectada; composição deve ser preservada")
    if face_count == 1 and (speaker_confidence is None or speaker_confidence >= 0.75):
        if _truthy(data.get("close_up")) or _truthy(data.get("is_selfie")):
            return _profile("selfie_proximo", 0.72, "uma face estável em plano próximo")
        return _profile("talking_head", 0.70, "uma face detectada com confiança suficiente")

    return _profile("desconhecido", 0.35, "não há evidência audiovisual estruturada suficiente")


def _profile(family: str, confidence: float, reason: str) -> dict[str, Any]:
    normalized = _normalize_label(family)
    if normalized not in KNOWN_FORMATS:
        normalized = "desconhecido"
        confidence = min(confidence, 0.35)
        reason = "formato declarado não reconhecido; preservação conservadora"
    preserve = normalized in _PRESERVE_COMPOSITION
    return {
        "visual_format": normalized,
        "visual_format_confidence": round(max(0.0, min(1.0, confidence)), 2),
        "visual_format_reason": reason,
        "reframe_policy": "preservar_composicao" if preserve else "reframe_se_seguro",
        "preserve_composition": preserve,
    }


def _first_known(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _normalize_label(data.get(key))
        if value in KNOWN_FORMATS and value != "desconhecido":
            return value
    return ""


def _normalize_label(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in _TRUE_VALUES
    return value in _TRUE_VALUES


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)
