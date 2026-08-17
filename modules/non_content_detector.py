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

import json
import re
import unicodedata
from pathlib import Path
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

# Half-way between the highest score seen on real argument (0.0) and the lowest
# seen on real filler (0.389), leaving room for a stretch that mixes the two.
LEARNED_NON_CONTENT_THRESHOLD = 0.15

_PRIORS_PATH = Path(__file__).resolve().parent.parent / "data" / "chub_priors" / "acervo_priors.json"
_PRIORS_CACHE: dict[str, Any] | None = None


def load_priors() -> dict[str, Any]:
    """Statistics distilled from the Acervo corpus, carried locally.

    The hand-written cue lists below were a guess and recovered 3.4% of the
    regions the Acervo labelled. These terms were learned instead, from the
    frequency gap between sentences inside a block and sentences inside a
    labelled non-content region across 885k sentences. They surfaced whole
    categories the guess had missed — sponsorship, donation nicknames, channel
    jargon — and no transcript travels with them, only the odds of each word.

    Missing or unreadable priors leave the detector on its hand-written cues
    alone, so the app keeps working offline with no extra file.
    """
    global _PRIORS_CACHE
    if _PRIORS_CACHE is None:
        try:
            _PRIORS_CACHE = json.loads(_PRIORS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _PRIORS_CACHE = {}
    return _PRIORS_CACHE


def learned_non_content_score(text: str) -> tuple[float, list[str]]:
    """Mean log-odds of the learned terms present, and which ones they were."""
    priors = load_priors()
    terms = priors.get("non_content_terms") or {}
    if not terms:
        return 0.0, []
    words = _WORD.findall(_normalize(text))
    if not words:
        return 0.0, []
    hits = [(word, terms[word]) for word in words if word in terms]
    if not hits:
        return 0.0, []
    # Averaged over the whole stretch, so one promotional word inside a long
    # argument cannot condemn it, while a run of them adds up.
    total = sum(weight for _, weight in hits)
    return total / len(words), [word for word, _ in hits[:8]]


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

    # Density of learned promotional vocabulary, weighted by how strongly each
    # term marks non-content in the corpus. An earlier 86-term lexicon could not
    # separate the two classes; with the vocabulary extended to the whole
    # promotional, production and sign-off surface the gap is unambiguous. On the
    # real sponsor read of a 47-minute interview it reaches 0.437 and on the
    # closing thanks 0.389, while four passages of actual argument from the same
    # interview — penal law, the Supreme Court, urban policy, municipalities —
    # all score exactly 0.
    learned, learned_terms = learned_non_content_score(normalized)
    if learned >= LEARNED_NON_CONTENT_THRESHOLD:
        cues.append("lexico_aprendido")

    # A single decisive cue is enough; otherwise two independent ones must agree.
    decisive = (
        unintelligible
        or "engajamento" in cues
        or repetition >= 0.62
        or learned >= LEARNED_NON_CONTENT_THRESHOLD
    )
    non_content = decisive or len(cues) >= 2
    return {
        "non_content": non_content,
        "cues": cues,
        "repetition_ratio": round(repetition, 3),
        "learned_score": round(learned, 3),
        "learned_terms": learned_terms,
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
