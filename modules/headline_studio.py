"""Headline studio for short-form political video artwork.

Turns a finished cut into *text for the artwork*, not SEO metadata, in the two
production formats the editor uses: vertical headline and square "Alfinetei".

The copy itself is built in ``headline_quote``, in three parts — stamp,
attribution and a **literal** quote. This module is the studio around it: the
format profiles, the line budget, the topic reading, the learning from the
editor's past choices and the optional online refinement.

Local suggestions are always available. An online model may improve the stamp
and the attribution; it can never touch the quote, because a quote it rewrote is
a quote nobody said.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from modules.headline_quote import (
    Speaker,
    compose,
    pick_quotes,
    sentences_from_segments,
    sentences_from_text,
)
from modules.political_profile import analyze_political_text, normalize
from modules.transcript_parser import parse_transcript_text


FORMAT_VERTICAL = "vertical_916"
FORMAT_SQUARE = "square_alfinetei"
# O formato "fake tweet" saiu: o editor pediu para descartá-lo e ele continuava
# no módulo, na interface e no seletor de formato. Não confundir com o
# `visual_format: "fake_tweet"` de `editorial_format`, que é outra coisa — lá é a
# composição observada *dentro* da fonte, e essa continua existindo.
FORMAT_IDS = {FORMAT_VERTICAL, FORMAT_SQUARE}

FORMAT_PROFILES = {
    FORMAT_VERTICAL: {
        "label": "9:16 — headline central",
        "description": "Texto preto em faixa amarela; destaque pontual branco em vermelho quando houver conflito explicitamente dito.",
        "headline_limit": 58,
        "eyebrow_limit": 18,
        "max_lines": 3,
        "ideal_line_chars": 19,
        "copy_role": "headline central de leitura imediata",
    },
    FORMAT_SQUARE: {
        "label": "1:1 — Alfinetei",
        "description": "Uma chamada curta no topo e headline branca, enxuta, em até três linhas. Não é uma descrição de publicação.",
        "headline_limit": 64,
        "eyebrow_limit": 18,
        "max_lines": 3,
        "ideal_line_chars": 23,
        "copy_role": "chamada superior curta e tese branca complementar",
    },
}

TOPIC_RULES = (
    ("cripto", ("bitcoin", "cripto", "criptomoeda", "criptomoedas", "blockchain")),
    ("emendas", ("emenda", "emendas", "parlamentar", "parlamentares", "orçamento", "orcamento", "indicadores")),
    ("mobilização", ("ato", "atos", "faculdade", "comparecer", "vão", "vá", "familia", "medo", "ameaça", "ameacas")),
    ("segurança", ("segurança", "seguranca", "crime", "polícia", "policia", "violência", "violencia", "bandido")),
    ("impostos", ("imposto", "tributo", "tributação", "tributacao", "iof", "taxa")),
    ("economia", ("economia", "emprego", "salário", "salario", "inflação", "inflacao", "pobreza")),
    ("liberdade", ("liberdade", "censura", "regular", "regulação", "regulacao", "estado")),
    ("política", ("brasil", "governo", "presidente", "congresso", "stf", "eleição", "eleicao", "política", "politica")),
)

ATTENTION_WORDS = ("ALERTA", "ARCAICO", "ABSURDO", "ATENÇÃO", "URGENTE", "IMPRESSIONANTE")


@dataclass(frozen=True)
class ArtworkSuggestion:
    eyebrow: str
    headline: str
    emphasis: str = ""
    accent: str = "none"
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        profile = FORMAT_PROFILES.get(self.note, {})
        lines = _break_headline(
            self.headline,
            max_lines=int(profile.get("max_lines", 3)),
            ideal_line_chars=int(profile.get("ideal_line_chars", 22)),
        )
        return {
            "eyebrow": self.eyebrow,
            "headline": self.headline,
            "headline_lines": lines,
            "emphasis": self.emphasis,
            "accent": self.accent,
            "character_count": len(self.headline),
            "word_count": len(self.headline.split()),
            "layout_hint": f"até {profile.get('max_lines', 3)} linhas de cerca de {profile.get('ideal_line_chars', 22)} caracteres",
        }


def _compact(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;–—-")
    if len(text) <= limit:
        return text
    short = text[: limit + 1].rsplit(" ", 1)[0].strip()
    return short or text[:limit].strip()


def _break_headline(value: str, max_lines: int = 3, ideal_line_chars: int = 22) -> list[str]:
    """Break artwork copy into balanced lines without silently truncating the claim."""
    words = re.sub(r"\s+", " ", str(value or "")).strip().split()
    if not words:
        return []
    if len(words) <= 3:
        return [" ".join(words)]

    max_lines = max(1, int(max_lines))
    # The mathematical target prevents the final line becoming a visual orphan;
    # the profile target keeps the result close to the channel's reference layouts.
    balanced_target = max(11, round(len(" ".join(words)) / max_lines))
    target = max(11, min(int(ideal_line_chars), balanced_target + 4))
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        remaining_words = len(words) - (sum(len(line.split()) for line in lines) + len(current))
        remaining_lines = max_lines - len(lines)
        should_wrap = (
            current
            and len(candidate) > target
            and len(lines) < max_lines - 1
            and remaining_words >= remaining_lines
        )
        if should_wrap:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))

    # In the rare case of a long claim, keep all its words in the final line.
    # The caller can warn through layout_hint instead of turning a claim into a lie.
    if len(lines) > max_lines:
        lines = [*lines[: max_lines - 1], " ".join(lines[max_lines - 1 :])]
    return lines


def _coerce_text(transcript: str) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """O texto, o que se sabe sobre ele, e as linhas com tempo quando existem.

    As linhas passaram a ser devolvidas porque a citação precisa do instante em
    que foi dita: é ele que deixa o editor conferir no áudio, e o áudio é a fonte
    da verdade. Antes só o texto corrido saía daqui, e o timestamp — que a fonte
    trazia — era jogado fora na porta de entrada.
    """
    raw = str(transcript or "").strip()
    if not raw:
        raise ValueError("Cole ou importe uma transcrição antes de gerar o texto de arte.")
    try:
        parsed = parse_transcript_text(raw)
        return parsed["full_text"], {
            "format": parsed.get("format", "timestamped"),
            "segment_count": parsed.get("segment_count", 0),
            "timestamped": True,
        }, list(parsed.get("segments") or [])
    except ValueError:
        # Finished edits often arrive as a clean text export without timestamps.
        plain = re.sub(r"\s+", " ", raw).strip()
        if len(plain.split()) < 4:
            raise ValueError("A transcrição precisa ter ao menos uma frase curta para análise.")
        return plain, {"format": "plain_text", "segment_count": 0, "timestamped": False}, []


def _topic(text: str) -> str:
    """Choose the strongest evidenced topic, not the first substring match."""
    folded = normalize(text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    best = "política"
    best_hits = 0
    best_evidence: list[str] = []
    for label, terms in TOPIC_RULES:
        evidence = []
        for term in terms:
            normalized_term = normalize(term)
            if not normalized_term:
                continue
            if " " in normalized_term:
                present = normalized_term in folded
            else:
                present = normalized_term in tokens
            if present:
                evidence.append(normalized_term)
        if len(evidence) > best_hits:
            best, best_hits, best_evidence = label, len(evidence), evidence
    return best


def _topic_evidence(text: str, topic: str) -> list[str]:
    folded = normalize(text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    for label, terms in TOPIC_RULES:
        if label != topic:
            continue
        evidence = []
        for term in terms:
            normalized_term = normalize(term)
            if (" " in normalized_term and normalized_term in folded) or (" " not in normalized_term and normalized_term in tokens):
                evidence.append(normalized_term)
        return evidence[:6]
    return []


def _speaker_from_context(mini_context: str, speaker_name: str = "", speaker_level: str = "") -> Speaker:
    """Quem assina a fala, e quem respondeu por isso.

    Deduzir o locutor do próprio texto é o chute que o NORTE proíbe: um corte que
    atribui uma fala a quem não a disse não custa um corte, custa a conta. Então
    o nome só entra por dois caminhos, e os dois têm alguém por trás — o
    reconhecimento de voz, que bateu com a amostra cadastrada, ou o editor, que
    escreveu de quem é a fonte. Sem nenhum dos dois a headline sai sem nome.
    """
    if speaker_name.strip() and speaker_level in {"audio", "editor"}:
        return Speaker(name=speaker_name.strip(), level=speaker_level)
    folded = normalize(mini_context)
    if "renan santos" in folded:
        return Speaker(name="Renan Santos", level="editor")
    if re.search(r"\brenan\b", folded):
        return Speaker(name="Renan", level="editor")
    return Speaker()


def _quote_span(headline: str) -> str:
    """O trecho entre aspas de uma headline montada."""
    match = re.search(r"[\u201c\"']([^\u201d\"']{4,})[\u201d\"']", str(headline or ""))
    return match.group(1).strip() if match else ""


def _quote_is_verbatim(headline: str, source_text: str) -> bool:
    """A citação dentro desta headline foi mesmo dita, palavra por palavra?

    É o portão do caminho de IA. O modelo pode melhorar a estampa e a atribuição;
    ele não pode tocar na citação, porque uma citação reescrita é uma citação
    falsa, ainda que o sentido pareça o mesmo. O corte por reticências é aceito
    porque ele remove pelo fim e diz que removeu.
    """
    trecho = _quote_span(headline)
    if not trecho:
        return False
    alvo = normalize(trecho.rstrip("\u2026. ")).strip()
    if len(alvo.split()) < 4:
        return False
    return alvo in normalize(source_text)


def _format_from_learning(editorial_learning: dict[str, Any] | None) -> tuple[str, int, str]:
    """Use only aggregate editor choices once the local sample is meaningful."""
    if not isinstance(editorial_learning, dict):
        return "", 0, ""
    topic_counts = editorial_learning.get("topic_by_format")
    overall_counts = editorial_learning.get("overall_by_format")
    if isinstance(topic_counts, dict) and topic_counts:
        leader, count = max(topic_counts.items(), key=lambda item: int(item[1] or 0))
        if leader in FORMAT_IDS and int(count or 0) >= 2:
            return leader, int(count), "neste tema"
    if isinstance(overall_counts, dict) and overall_counts:
        leader, count = max(overall_counts.items(), key=lambda item: int(item[1] or 0))
        if leader in FORMAT_IDS and int(count or 0) >= 4:
            return leader, int(count), "no seu histórico geral"
    return "", 0, ""


def _suggestion_from_quote(built: dict[str, Any], format_id: str) -> dict[str, Any]:
    """Uma sugestão de arte no contrato que a interface já lê.

    A estampa vira a chamada de cima e a citação, com a atribuição na frente,
    vira a headline — exatamente a forma da headline que o editor aprovou. A
    citação não passa por `_compact`: truncar no meio de uma palavra é
    parafrasear sem dizer que parafraseou, e é o que o invariante proíbe.
    """
    profile = FORMAT_PROFILES[format_id]
    headline = built["headline"]
    return {
        "eyebrow": _compact(built["stamp"], int(profile["eyebrow_limit"])).upper() if profile["eyebrow_limit"] else "",
        "headline": headline,
        "headline_lines": _break_headline(
            headline,
            max_lines=int(profile["max_lines"]),
            ideal_line_chars=int(profile["ideal_line_chars"]),
        ),
        "emphasis": "",
        "accent": "red_on_white" if format_id == FORMAT_VERTICAL else "white",
        "character_count": len(headline),
        "word_count": len(headline.split()),
        "layout_hint": f"até {profile['max_lines']} linhas de cerca de {profile['ideal_line_chars']} caracteres",
        # O que permite conferir a citação no áudio, que é a fonte da verdade.
        "quote": built["quote"],
        "attribution": built["attribution"],
        "attribution_level": built["attribution_level"],
        "stamp_alternatives": built["stamp_alternatives"],
        "within_preferred_limit": len(headline) <= int(profile["headline_limit"]),
    }


def _fallback_result(
    text: str,
    mini_context: str,
    preferred_format: str,
    editorial_learning: dict[str, Any] | None = None,
    segments: list[dict[str, Any]] | None = None,
    speaker: Speaker | None = None,
) -> dict[str, Any]:
    from modules.interview_turns import is_interviewer_sentence

    signals = analyze_political_text(text, user_context=mini_context)
    topic = _topic(text)
    falante = speaker or Speaker()

    frases = sentences_from_segments(segments) if segments else sentences_from_text(text)
    citacoes = pick_quotes(frases, wanted=3, is_other_speaker=is_interviewer_sentence)
    montadas = [compose(item, falante, signals) for item in citacoes]

    selected_only = preferred_format if preferred_format in FORMAT_IDS else ""
    square = [_suggestion_from_quote(item, FORMAT_SQUARE) for item in montadas] \
        if not selected_only or selected_only == FORMAT_SQUARE else []
    vertical = [_suggestion_from_quote(item, FORMAT_VERTICAL) for item in montadas] \
        if not selected_only or selected_only == FORMAT_VERTICAL else []

    learning_format, learning_count, learning_scope = _format_from_learning(editorial_learning)
    learning_applied = False
    if preferred_format in FORMAT_IDS:
        recommended = preferred_format
    elif learning_format:
        recommended = learning_format
        learning_applied = True
    elif signals.get("claim_strength", 0) >= 45 and len(text.split()) >= 35:
        recommended = FORMAT_SQUARE
    else:
        recommended = FORMAT_VERTICAL

    is_complete = text.rstrip().endswith((".", "!", "?"))
    review_flags = {
        "needs_fact_review": bool(signals.get("needs_fact_review")),
        "needs_legal_review": bool(signals.get("needs_legal_review")),
        "transcript_ends_incomplete": not is_complete,
        # Sem atribuição a arte sai sem nome, e o editor precisa saber por quê.
        "speaker_unconfirmed": not falante.confirmed,
        # Silêncio é defeito: quando nenhuma frase se sustenta, isso é dito.
        "no_quote_found": not montadas,
        # A fonte não pontua, então a fronteira da citação veio do silêncio. Ela
        # é real — o orador respirou ali — mas não é fim de frase, e as aspas
        # precisam ser conferidas no áudio antes de irem para a arte.
        "quote_boundary_from_pause": any(
            item["quote"].get("boundary_source") == "pausa" for item in montadas
        ),
    }
    recommendation_reason = {
        FORMAT_SQUARE: "A tese tem desenvolvimento suficiente para uma chamada curta no topo e a citação em até três linhas.",
        FORMAT_VERTICAL: "A citação é curta o bastante para ser lida de uma vez como headline central.",
    }[recommended]
    if learning_applied:
        recommendation_reason = (
            f"O formato foi priorizado por {learning_count} escolha(s) aprovada(s) {learning_scope}; "
            "o texto continua sendo gerado a partir desta transcrição."
        )
    if not montadas:
        recommendation_reason = (
            "Nenhuma frase deste corte se sustenta sozinha como citação: todas continuam a "
            "anterior, são protocolo do programa ou vieram cortadas pela legenda."
        )

    return {
        "recommended_format": recommended,
        "recommendation_reason": recommendation_reason,
        "topic": topic,
        "topic_evidence": _topic_evidence(text, topic),
        "attention_word": montadas[0]["stamp"] if montadas else "",
        "speaker": {"name": falante.name, "level": falante.level, "confirmed": falante.confirmed},
        "quotes_rejected": len(frases) - len(citacoes),
        "formats": {
            FORMAT_VERTICAL: {**FORMAT_PROFILES[FORMAT_VERTICAL], "suggestions": vertical},
            FORMAT_SQUARE: {**FORMAT_PROFILES[FORMAT_SQUARE], "suggestions": square},
        },
        "review_flags": review_flags,
        "analysis": {
            "editorial_family": signals.get("editorial_family", "conversa"),
            "context_completeness": signals.get("context_completeness", 0),
            "claim_strength": signals.get("claim_strength", 0),
            "conflict_or_stakes": signals.get("conflict_or_stakes", 0),
        },
        "generation_source": "literal_quote",
        "learning_applied": {
            "applied": learning_applied,
            "format_id": learning_format if learning_applied else "",
            "selected_count": learning_count if learning_applied else 0,
            "scope": learning_scope if learning_applied else "",
        },
    }


def _extract_json(value: str) -> dict[str, Any] | None:
    raw = str(value or "").strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _suggestion_has_evidence(value: str, source_text: str) -> bool:
    source_tokens = set(re.findall(r"[a-z0-9]+", normalize(source_text)))
    suggestion_tokens = [token for token in re.findall(r"[a-z0-9]+", normalize(value)) if len(token) >= 5]
    stopwords = {"sobre", "depois", "agora", "brasil", "verdade", "precisa", "explica", "debate", "rumo"}
    meaningful = [token for token in suggestion_tokens if token not in stopwords]
    return bool(meaningful and any(token in source_tokens for token in meaningful))


def _merge_ai_suggestions(
    base: dict[str, Any],
    payload: dict[str, Any],
    source_text: str = "",
    preferred_format: str = "auto",
) -> dict[str, Any]:
    """Aceitar variações do modelo apenas onde a citação continua sendo literal.

    O portão mudou de natureza. Antes bastava a headline compartilhar palavras
    com a transcrição, e por isso o modelo podia reescrever a frase mantendo o
    vocabulário — que é exatamente uma paráfrase. Agora a citação entre aspas tem
    de aparecer palavra por palavra na fonte, senão a variação é descartada e a
    versão determinística fica de pé.
    """
    suggested = payload.get("formats") if isinstance(payload, dict) else None
    if not isinstance(suggested, dict):
        return base
    allowed_formats = (preferred_format,) if preferred_format in FORMAT_IDS else (FORMAT_VERTICAL, FORMAT_SQUARE)
    aceitou_alguma = False
    for format_id in allowed_formats:
        variants = suggested.get(format_id)
        if not isinstance(variants, list):
            continue
        profile = FORMAT_PROFILES[format_id]
        originais = {
            item.get("quote", {}).get("text", ""): item
            for item in base["formats"][format_id]["suggestions"]
        }
        accepted = []
        for item in variants[:3]:
            if not isinstance(item, dict):
                continue
            headline = re.sub(r"\s+", " ", str(item.get("headline", ""))).strip()
            if len(headline.split()) < 3:
                continue
            if not _quote_is_verbatim(headline, source_text):
                continue
            # A sugestão do modelo herda a proveniência da citação que ela cita,
            # para o editor continuar podendo conferir no áudio.
            trecho = _quote_span(headline).rstrip("\u2026. ")
            origem = next(
                (valor for chave, valor in originais.items() if normalize(trecho) in normalize(chave)),
                None,
            )
            eyebrow = _compact(str(item.get("eyebrow", "")), int(profile["eyebrow_limit"])).upper()
            accepted.append({
                "eyebrow": eyebrow,
                "headline": headline,
                "headline_lines": _break_headline(
                    headline,
                    max_lines=int(profile["max_lines"]),
                    ideal_line_chars=int(profile["ideal_line_chars"]),
                ),
                "emphasis": "",
                "accent": "red_on_white" if item.get("accent") == "red_on_white" else "white",
                "character_count": len(headline),
                "word_count": len(headline.split()),
                "layout_hint": f"até {profile['max_lines']} linhas de cerca de {profile['ideal_line_chars']} caracteres",
                "quote": (origem or {}).get("quote", {"text": trecho, "verbatim": True, "start_s": None, "end_s": None}),
                "attribution": (origem or {}).get("attribution", ""),
                "attribution_level": (origem or {}).get("attribution_level", "nao_atribuida"),
                "stamp_alternatives": (origem or {}).get("stamp_alternatives", []),
                "within_preferred_limit": len(headline) <= int(profile["headline_limit"]),
            })
        if accepted:
            base["formats"][format_id]["suggestions"] = accepted
            aceitou_alguma = True
    requested = payload.get("recommended_format")
    if requested in FORMAT_IDS:
        base["recommended_format"] = requested
    if isinstance(payload.get("recommendation_reason"), str):
        base["recommendation_reason"] = _compact(payload["recommendation_reason"], 220)
    if aceitou_alguma:
        base["generation_source"] = "ai_refined"
    return base


def generate_artwork_copy(
    transcript: str,
    mini_context: str = "",
    preferred_format: str = "auto",
    ai_backend: Any | None = None,
    emit_progress=None,
    editorial_learning: dict[str, Any] | None = None,
    segments: list[dict[str, Any]] | None = None,
    speaker_name: str = "",
    speaker_level: str = "",
) -> dict[str, Any]:
    """Texto de arte a partir de um corte pronto: estampa, atribuição e citação.

    ``segments`` são as linhas com tempo, quando quem chama as tem. Sem elas a
    citação continua literal, mas sai sem o instante em que foi dita — e o
    instante é o que permite ao editor conferir no áudio, que é a fonte da
    verdade. ``speaker_level`` é ``"audio"`` quando o reconhecimento de voz
    respondeu por quem fala, e só nesse caso a atribuição ganha verbo forte.
    """
    text, transcript_meta, parsed_segments = _coerce_text(transcript)
    context = _compact(mini_context, 280)
    preferred = preferred_format if preferred_format in FORMAT_IDS else "auto"
    falante = _speaker_from_context(context, speaker_name, speaker_level)
    linhas = segments if segments else parsed_segments
    result = _fallback_result(
        text, context, preferred,
        editorial_learning=editorial_learning,
        segments=linhas,
        speaker=falante,
    )
    result["transcript"] = {
        **transcript_meta,
        "word_count": len(text.split()),
        "excerpt": _compact(text, 280),
    }
    result["mini_context"] = context

    if ai_backend is not None:
        if emit_progress:
            emit_progress("[Texto de arte] Refinando estampa e atribuição pelo modo de IA configurado...", "info")
        citacoes = [
            item["quote"]["text"]
            for formato in result["formats"].values()
            for item in formato["suggestions"]
        ]
        system = (
            "Você é editor de vídeos políticos curtos no Brasil e escreve texto de ARTE, não SEO.\n"
            "A headline tem três partes: uma estampa curta, a atribuição e a CITAÇÃO entre aspas.\n"
            "A CITAÇÃO É LITERAL. Copie-a exatamente de uma das citações fornecidas, sem trocar, "
            "acrescentar ou remover uma única palavra. Você pode escolher qual citação usar e pode "
            "mudar a estampa; reescrever a citação invalida a sugestão inteira.\n"
            "Não invente fatos, crimes, números, intenções ou acusações. Não atribua a fala a "
            "ninguém que não esteja na atribuição fornecida.\n"
            "Responda somente JSON válido."
        )
        aspas = "\n".join(f'- "{item}"' for item in citacoes) or "(nenhuma)"
        atribuicao = result["formats"][preferred if preferred in FORMAT_IDS else FORMAT_VERTICAL]["suggestions"]
        prefixo = atribuicao[0]["attribution"] if atribuicao else ""
        prompt = (
            f"CITAÇÕES DISPONÍVEIS (copie uma delas ao pé da letra):\n{aspas}\n\n"
            f"ATRIBUIÇÃO A USAR (ou vazio, e então não atribua a ninguém): {prefixo or '(nenhuma)'}\n\n"
            f"MINICONTEXTO DO EDITOR: {context or '(nenhum)'}\n\n"
            "Produza JSON:\n"
            "{\n"
            '  "recommended_format": "vertical_916|square_alfinetei",\n'
            '  "recommendation_reason": "motivo breve",\n'
            '  "formats": {\n'
            '    "vertical_916": [{"eyebrow":"estampa curta", "headline":"ATRIBUIÇÃO \u201ccitação literal\u201d"}],\n'
            '    "square_alfinetei": [{"eyebrow":"estampa curta", "headline":"ATRIBUIÇÃO \u201ccitação literal\u201d"}]\n'
            "  }\n"
            "}\n"
            "No máximo 3 alternativas por formato."
        )
        try:
            refined = _extract_json(ai_backend.generate(prompt, system, emit_progress))
            if refined:
                result = _merge_ai_suggestions(result, refined, source_text=text, preferred_format=preferred)
        except Exception:
            # Uma saída determinística e explicável é melhor que uma tela quebrada.
            pass
    result["generated_format"] = preferred if preferred in FORMAT_IDS else result.get("recommended_format", FORMAT_VERTICAL)
    return result
