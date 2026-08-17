"""Find stretches of a transcript that hold no editorial content.

The Acervo labels these regions for every video it processes, and feeding them to
the selector removed a quarter of the wasted candidates. That only helps for
sources the Acervo already labelled: a fresh recording arrives with nothing.

This module gives Furia the same judgement natively, from the transcript alone.
It was written against the regions the Acervo labelled on two real sources and is
measured against them, so the agreement is a number and not an impression.

The detector is deliberately conservative. Discarding a stretch of real speech is
worse than keeping a weak candidate, so a region is only reported when several
independent cues agree, or when a single cue is decisive on its own.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


# Openings, closings and engagement requests. These are the phrases a broadcast
# uses around the content, never inside an argument.
_OPENING = (
    "boa noite", "boa tarde", "bom dia", "sejam bem-vindos", "seja bem-vindo",
    "bem-vindos ao", "bem vindos ao", "senhoras e senhores", "começa agora",
    "mais um episódio", "convidado de hoje", "nosso convidado",
)
_CLOSING = (
    "muito obrigad", "obrigado pela entrevista", "até a próxima", "um abraço",
    "foi um prazer", "encerramos por aqui", "fica com deus", "boa noite a todos",
)
_ENGAGEMENT = (
    "dando like", "deixa o like", "deixe o like", "se inscreve", "se inscrever",
    "inscreva-se", "ativa o sininho", "compartilha a live", "compartilhem",
    "divulga a live", "chegar a 14", "meta de", "manda um pix", "link na descrição",
)
_PRODUCTION = (
    "qual câmera", "que câmera", "tá no ar", "está no ar", "microfone",
    "o áudio tá", "áudio está", "testando", "sobe o som", "corta aí",
    "coloca na tela", "bota na tela", "põe na tela", "transmissão caiu",
)

_CUE_GROUPS = {
    "abertura": _OPENING,
    "encerramento": _CLOSING,
    "engajamento": _ENGAGEMENT,
    "producao": _PRODUCTION,
}

_WORD = re.compile(r"[0-9a-zà-ü]+")


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower()
    return " ".join(lowered.split())


def _latin_ratio(text: str) -> float:
    """Share of letters that belong to the Latin script.

    One labelled region was the single token ``เฮ เฮ`` — caption noise from a
    stretch with no intelligible speech at all.
    """
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    latin = sum(1 for char in letters if "LATIN" in unicodedata.name(char, ""))
    return latin / len(letters)


def _repetition_ratio(text: str, size: int = 4) -> float:
    """How much of the text is repeated phrasing, as a jingle or chant is.

    Measured over word sequences rather than single words. A subject being
    developed returns to its key terms constantly — a block about taxation says
    "imposto" in every other sentence — so counting single words marks any
    focused argument as repetitive. What a chant repeats is the whole phrase.
    """
    words = _WORD.findall(_normalize(text))
    if len(words) < size * 3:
        return 0.0
    grams = [tuple(words[index:index + size]) for index in range(len(words) - size + 1)]
    return 1.0 - (len(set(grams)) / len(grams))


def score_segment(text: str, *, words_per_second: float | None = None) -> dict[str, Any]:
    """Weigh the evidence that one stretch of transcript carries no content."""
    normalized = _normalize(text)
    words = _WORD.findall(normalized)
    cues: list[str] = []

    for label, phrases in _CUE_GROUPS.items():
        if any(phrase in normalized for phrase in phrases):
            cues.append(label)

    repetition = _repetition_ratio(normalized)
    if repetition >= 0.62:
        cues.append("repeticao")

    latin = _latin_ratio(normalized)
    # Text made of letters that yield no readable word at all is caption noise:
    # the word pattern only matches Latin script, so a stretch in another script
    # produces letters but zero words.
    has_letters = any(char.isalpha() for char in normalized)
    unintelligible = (bool(words) and latin < 0.5) or (has_letters and not words)
    if unintelligible:
        cues.append("ininteligivel")

    # Long stretches with very little speech are silence, applause or music
    # rather than an argument being made.
    sparse = bool(words_per_second is not None and words_per_second < 0.55 and len(words) < 40)
    if sparse:
        cues.append("fala_esparsa")

    # A single decisive cue is enough; otherwise two independent ones must agree.
    decisive = unintelligible or "engajamento" in cues or repetition >= 0.62
    non_content = decisive or len(cues) >= 2
    return {
        "non_content": non_content,
        "cues": cues,
        "repetition_ratio": round(repetition, 3),
        "latin_ratio": round(latin, 3),
        "word_count": len(words),
    }


def detect_non_content_regions(
    segments: list[dict[str, Any]],
    *,
    window: int = 4,
    min_duration_s: float = 4.0,
) -> list[dict[str, Any]]:
    """Report stretches of the transcript that read as non-content.

    Sentences are judged in small overlapping windows rather than one by one: a
    greeting is one sentence, but production chatter and casual banter only look
    like themselves across several. Adjacent hits are merged so the caller
    receives regions, in the same shape the Acervo publishes them.
    """
    usable = [
        item for item in segments or []
        if str(item.get("text") or "").strip()
        and float(item.get("end", 0) or 0) > float(item.get("start", 0) or 0)
    ]
    if not usable:
        return []

    flagged: list[tuple[float, float, list[str]]] = []
    for index in range(len(usable)):
        group = usable[index:index + window]
        start = float(group[0].get("start", 0) or 0)
        end = float(group[-1].get("end", 0) or 0)
        span = max(0.001, end - start)
        text = " ".join(str(item.get("text") or "") for item in group)
        verdict = score_segment(text, words_per_second=len(_WORD.findall(_normalize(text))) / span)
        if verdict["non_content"]:
            flagged.append((start, end, verdict["cues"]))

    if not flagged:
        return []

    regions: list[dict[str, Any]] = []
    current_start, current_end, current_cues = flagged[0]
    for start, end, cues in flagged[1:]:
        if start <= current_end + 1.0:
            current_end = max(current_end, end)
            current_cues = list(dict.fromkeys(current_cues + cues))
        else:
            regions.append({"start_s": current_start, "end_s": current_end, "cues": current_cues})
            current_start, current_end, current_cues = start, end, cues
    regions.append({"start_s": current_start, "end_s": current_end, "cues": current_cues})

    return [
        {
            **region,
            "duration_s": round(region["end_s"] - region["start_s"], 3),
            "reason": "Sem conteúdo editorial: " + ", ".join(region["cues"]),
            "provenance": "furia_local_detector",
        }
        for region in regions
        if region["end_s"] - region["start_s"] >= min_duration_s
    ]
