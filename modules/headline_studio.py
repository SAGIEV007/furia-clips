"""Headline studio for short-form political video artwork.

This module turns a finished-cut transcript into *text for the artwork*, not SEO
metadata.  It keeps the three production formats used by the editor separate:
vertical headline, square "Alfinetei" and simulated post.  Local suggestions are
always available; an online model may improve wording but can never remove
context, attribution or review warnings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from modules.political_profile import analyze_political_text, normalize
from modules.transcript_parser import parse_transcript_text


FORMAT_VERTICAL = "vertical_916"
FORMAT_SQUARE = "square_alfinetei"
FORMAT_TWEET = "fake_tweet"
FORMAT_IDS = {FORMAT_VERTICAL, FORMAT_SQUARE, FORMAT_TWEET}

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
    FORMAT_TWEET: {
        "label": "Fake tweet — publicação simulada",
        "description": "Texto em primeira pessoa somente quando ele estiver inequívoco no corte; revisar antes de atribuir a postagem ao perfil.",
        "headline_limit": 180,
        "eyebrow_limit": 0,
        "max_lines": 5,
        "ideal_line_chars": 36,
        "copy_role": "rascunho conciso de publicação atribuível após revisão",
    },
}

TOPIC_RULES = (
    ("cripto", ("bitcoin", "cripto", "criptos", "crypto", "cryptos", "criptomoeda", "criptomoedas", "blockchain")),
    ("emendas", ("emenda", "emendas", "parlamentar", "parlamentares", "orçamento", "orcamento", "indicadores")),
    ("segurança", ("segurança", "seguranca", "crime", "polícia", "policia", "violência", "violencia", "bandido")),
    ("impostos", ("imposto", "impostos", "tributo", "tributos", "tributação", "tributacao", "tributar", "taxado", "taxação", "taxacao", "iof", "taxa")),
    ("economia", ("economia", "emprego", "salário", "salario", "inflação", "inflacao", "pobreza", "dívida", "divida", "despesa", "despesas", "benefício", "beneficios", "renúncia fiscal", "renuncia fiscal")),
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


def _transcript_ends_incomplete(value: str) -> bool:
    """Flag only visibly open endings; plain CapCut TXT often has no periods."""
    raw = re.sub(r"\s+", " ", str(value or "")).strip()
    if not raw:
        return True
    if raw.endswith((".", "!", "?")):
        return False
    if raw.endswith((",", ";", ":", "—", "-")):
        return True
    words = re.findall(r"[a-z0-9À-ÿ-]+", normalize(raw))
    return bool(words and words[-1] in {
        "porque", "mas", "porem", "se", "quando", "que", "como", "embora",
        "entao", "portanto", "logo", "de", "do", "da", "dos", "das", "em",
        "no", "na", "nos", "nas", "para", "por", "com", "sem", "e", "ou",
    })


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


def _coerce_text(transcript: str) -> tuple[str, dict[str, Any]]:
    raw = str(transcript or "").strip()
    if not raw:
        raise ValueError("Cole ou importe uma transcrição antes de gerar o texto de arte.")
    try:
        parsed = parse_transcript_text(raw)
        return parsed["full_text"], {
            "format": parsed.get("format", "timestamped"),
            "segment_count": parsed.get("segment_count", 0),
            "timestamped": True,
        }
    except ValueError:
        # Finished edits often arrive as a clean text export without timestamps.
        plain = re.sub(r"\s+", " ", raw).strip()
        if len(plain.split()) < 4:
            raise ValueError("A transcrição precisa ter ao menos uma frase curta para análise.")
        return plain, {"format": "plain_text", "segment_count": 0, "timestamped": False}


def _topic(text: str) -> str:
    """Choose the strongest evidenced topic using distinct terms and frequency.

    Synonyms such as ``salário``/``salario`` are deduplicated after accent
    normalization, so a duplicated spelling cannot beat a genuinely repeated
    topic such as impostos or despesas.
    """
    folded = normalize(text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    best = "política"
    best_score = 0.0
    for label, terms in TOPIC_RULES:
        normalized_terms = dict.fromkeys(normalize(term) for term in terms if normalize(term))
        distinct_hits = 0
        frequency_score = 0.0
        for normalized_term in normalized_terms:
            if " " in normalized_term:
                count = len(re.findall(r"(?<![a-z0-9])" + re.escape(normalized_term) + r"(?![a-z0-9])", folded))
            else:
                count = sum(1 for token in re.findall(r"[a-z0-9]+", folded) if token == normalized_term)
            if count:
                distinct_hits += 1
                frequency_score += min(3, count)
        score = distinct_hits * 1.5 + frequency_score
        if score > best_score:
            best, best_score = label, score
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
            present = (
                normalized_term in folded
                if " " in normalized_term
                else normalized_term in tokens
            )
            if present and normalized_term not in evidence:
                evidence.append(normalized_term)
        return evidence[:8]
    return []


def _attention_word(text: str, signals: dict[str, Any]) -> str:
    folded = normalize(text)
    if "arcaic" in folded:
        return "ARCAICO"
    if any(term in folded for term in ("urgente", "agora", "alerta")):
        return "ALERTA"
    if signals.get("conflict_or_stakes", 0) >= 55:
        return "ABSURDO"
    if signals.get("claim_strength", 0) >= 55:
        return "ATENÇÃO"
    return "IMPRESSIONANTE"


def _speaker_prefix(mini_context: str) -> str:
    """Return a short, explicit attribution only when the editor supplied it."""
    folded = normalize(mini_context)
    if "renan santos" in folded or re.search(r"\brenan\b", folded):
        return "RENAN:"
    return ""


def _claim_candidates(text: str, topic: str, speaker_prefix: str = "") -> list[str]:
    folded = normalize(text)
    candidates: list[str] = []
    if "caminho arcaico" in folded:
        candidates.append("BRASIL ESCOLHEU O CAMINHO ARCAICO")
    if "com ou sem o estado" in folded or "vao ocorrer de qualquer forma" in folded:
        candidates.append("AS CRIPTOS AVANÇAM COM OU SEM O ESTADO")
    if "reserva de valor" in folded and topic == "cripto":
        candidates.append("CRIPTOS SÃO O FUTURO DA RESERVA DE VALOR")
    if "tribut" in folded and topic == "cripto" and "cript" in folded:
        candidates.append("RENAN CRITICA A TRIBUTAÇÃO DAS CRIPTOS")
    if "estado" in folded and "amig" in folded:
        candidates.append("O ESTADO VAI ACOLHER OU AFASTAR AS CRIPTOS?")
    if "liberdade" in folded:
        candidates.append("A LIBERDADE NÃO CABE EM MAIS CONTROLE")
    if "seguran" in folded:
        candidates.append("SEGURANÇA NÃO SE RESOLVE COM DISCURSO")
    if "emenda" in folded or "emendas" in folded:
        if "flavio dino" in folded and "jornalista" in folded:
            candidates.append("FLÁVIO DINO E A CONTRADIÇÃO DAS EMENDAS")
        if "politica publica" in folded or "indicador" in folded or "resultado" in folded:
            candidates.append("EMENDAS PRECISAM ENTREGAR RESULTADOS")
        if "parlamentar" in folded and "orcamento" in folded:
            candidates.append("EMENDA NÃO PODE VIRAR ORÇAMENTO DE PARLAMENTAR")
        if "agua potavel" in folded and "praca" in folded:
            candidates.append("SEM ÁGUA, NÃO TEM PRAÇA")
    if ("pais pobre" in folded or "pais que e pobre" in folded) and "pais rico" in folded:
        candidates.append("PAÍS POBRE COBRA IMPOSTO DE PAÍS RICO")
    if "duzentos bilhoes" in folded or "200 bilhoes" in folded or "200 bilhões" in text.lower():
        candidates.extend([
            "MAIS DE 200 BILHÕES POR ANO EM DESPESAS",
            "A CONTA EXIGE MEXER NAS DESPESAS",
        ])
    if "cobra imposto" in folded and "pais rico" in folded:
        candidates.append("O BRASIL COBRA IMPOSTO DE PAÍS RICO")
    if "despesa" in folded and ("index" in folded or "benef" in folded or "aposent" in folded):
        candidates.append("A CONTA NÃO FECHA SEM REVER DESPESAS")
    if "baixar imposto" in folded or "abaixar imposto" in folded:
        candidates.append("REDUZIR IMPOSTO EXIGE MEXER NAS DESPESAS")
    if "imposto" in folded or "tribut" in folded:
        if "cobra imposto" in folded and "pais rico" in folded:
            candidates.append("O BRASIL COBRA IMPOSTO DE PAÍS RICO")
        elif "despesa" in folded:
            candidates.append("REDUZIR IMPOSTO EXIGE ENCARAR AS DESPESAS")
        else:
            candidates.append("O DEBATE SOBRE IMPOSTOS EXIGE UMA RESPOSTA CLARA")
    if not candidates:
        label = topic.upper()
        generic_claims = [
            f"EXPLICA O IMPASSE DA {label}",
            f"O BRASIL PRECISA DECIDIR O RUMO DA {label}",
            f"A VERDADE INCÔMODA SOBRE {label}",
        ]
        candidates.extend(
            [f"{speaker_prefix} {generic_claims[0]}".strip(), *generic_claims[1:]]
            if speaker_prefix
            else generic_claims
        )
    unique: list[str] = []
    for candidate in candidates:
        candidate_folded = normalize(candidate)
        already_attributed = candidate_folded.startswith("renan ") or candidate_folded.startswith("renan:")
        attributed = f"{speaker_prefix} {candidate}".strip() if speaker_prefix and not already_attributed else candidate
        item = _compact(attributed, 64).upper()
        if item and item not in unique:
            unique.append(item)
    return unique[:4]


def _safe_fake_tweet(text: str, topic: str, mini_context: str) -> list[str]:
    folded = normalize(text)
    lead = ""
    if ("pais pobre" in folded or "pais que e pobre" in folded) and "pais rico" in folded:
        lead = "O país é pobre, cobra imposto de país rico e vai precisar mexer nas despesas."
    elif "duzentos bilhoes" in folded or "200 bilhoes" in folded or "200 bilhões" in text.lower():
        lead = "A conta apresentada é direta: será preciso mexer em mais de 200 bilhões por ano nas despesas."
    elif "cobra imposto" in folded and "pais rico" in folded:
        lead = "O Brasil cobra imposto de país rico, mas precisa encarar a revisão das despesas."
    elif "caminho arcaico" in folded:
        lead = "O Brasil escolheu o caminho arcaico ao lidar com as criptos."
    elif "reserva de valor" in folded and topic == "cripto":
        lead = "As criptos já são uma reserva de valor para as novas gerações."
    elif "estado" in folded and "amig" in folded:
        lead = "A pergunta é simples: o Estado será amigável ou hostil à inovação?"
    else:
        lead = f"O debate sobre {topic} precisa olhar para o futuro, não para o medo."
    if mini_context:
        lead = _compact(f"{lead} {mini_context}", 180)
    return [_compact(lead, 180)]


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
    approved_prior = editorial_learning.get("approved_clip_prior")
    if isinstance(approved_prior, dict) and approved_prior.get("eligible"):
        approved_by_format = approved_prior.get("approved_by_format")
        if isinstance(approved_by_format, dict) and approved_by_format:
            leader, count = max(approved_by_format.items(), key=lambda item: int(item[1] or 0))
            if leader in FORMAT_IDS and int(count or 0) >= 4:
                return leader, int(count), "nos cortes aprovados locais"
    return "", 0, ""


def _fallback_result(
    text: str,
    mini_context: str,
    preferred_format: str,
    editorial_learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signals = analyze_political_text(text, user_context=mini_context)
    topic = _topic(text)
    attention = _attention_word(text, signals)
    claims = _claim_candidates(text, topic, speaker_prefix=_speaker_prefix(mini_context))
    selected_only = preferred_format if preferred_format in FORMAT_IDS else ""
    square = [
        ArtworkSuggestion(attention, claim, emphasis="", accent="white", note=FORMAT_SQUARE).as_dict()
        for claim in claims[:3]
    ] if not selected_only or selected_only == FORMAT_SQUARE else []
    vertical = [
        ArtworkSuggestion("", claim, emphasis=_compact(claim.split()[-1], 18), accent="red_on_white", note=FORMAT_VERTICAL).as_dict()
        for claim in claims[:3]
    ] if not selected_only or selected_only == FORMAT_VERTICAL else []
    fake_tweet = [
        {
            "post_text": copy,
            "character_count": len(copy),
            "attribution_note": "Use como rascunho de publicação; confirme a redação final antes de atribuir ao perfil.",
        }
        for copy in _safe_fake_tweet(text, topic, mini_context)
    ] if not selected_only or selected_only == FORMAT_TWEET else []

    learning_format, learning_count, learning_scope = _format_from_learning(editorial_learning)
    learning_applied = False
    if preferred_format in FORMAT_IDS:
        recommended = preferred_format
    elif learning_format:
        recommended = learning_format
        learning_applied = True
    elif signals.get("claim_strength", 0) >= 45 and len(text.split()) >= 35:
        recommended = FORMAT_SQUARE
    elif signals.get("editorial_family") in {"reacao", "humor"}:
        recommended = FORMAT_VERTICAL
    else:
        recommended = FORMAT_VERTICAL

    transcript_ends_incomplete = _transcript_ends_incomplete(text)
    review_flags = {
        "needs_fact_review": bool(signals.get("needs_fact_review")),
        "needs_legal_review": bool(signals.get("needs_legal_review")),
        "transcript_ends_incomplete": transcript_ends_incomplete,
    }
    recommendation_reason = {
        FORMAT_SQUARE: "A tese tem desenvolvimento suficiente para uma chamada curta no topo e uma headline branca em até três linhas.",
        FORMAT_VERTICAL: "O argumento possui conflito ou contraste que funciona melhor como headline central de leitura imediata.",
        FORMAT_TWEET: "O corte possui uma posição autoral que pode virar rascunho de publicação, desde que a atribuição final seja revisada.",
    }[recommended]
    if learning_applied:
        recommendation_reason = (
            f"O formato foi priorizado por {learning_count} escolha(s) aprovada(s) {learning_scope}; "
            "o texto continua sendo gerado a partir desta transcrição."
        )
    return {
        "recommended_format": recommended,
        "recommendation_reason": recommendation_reason,
        "topic": topic,
        "topic_evidence": _topic_evidence(text, topic),
        "attention_word": attention,
        "formats": {
            FORMAT_VERTICAL: {**FORMAT_PROFILES[FORMAT_VERTICAL], "suggestions": vertical},
            FORMAT_SQUARE: {**FORMAT_PROFILES[FORMAT_SQUARE], "suggestions": square},
            FORMAT_TWEET: {**FORMAT_PROFILES[FORMAT_TWEET], "suggestions": fake_tweet},
        },
        "review_flags": review_flags,
        "analysis": {
            "editorial_family": signals.get("editorial_family", "conversa"),
            "context_completeness": signals.get("context_completeness", 0),
            "claim_strength": signals.get("claim_strength", 0),
            "conflict_or_stakes": signals.get("conflict_or_stakes", 0),
            "approved_clip_prior": {
                "eligible": bool((editorial_learning or {}).get("approved_clip_prior", {}).get("eligible")) if isinstance((editorial_learning or {}).get("approved_clip_prior"), dict) else False,
                "approved_count": int((editorial_learning or {}).get("approved_clip_prior", {}).get("approved_count", 0) or 0) if isinstance((editorial_learning or {}).get("approved_clip_prior"), dict) else 0,
                "influence_scope": str((editorial_learning or {}).get("approved_clip_prior", {}).get("influence_scope", "") or "") if isinstance((editorial_learning or {}).get("approved_clip_prior"), dict) else "",
            },
        },
        "generation_source": "editorial_fallback",
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
    """Require more than one source anchor before accepting an AI variation."""
    source_tokens = set(re.findall(r"[a-z0-9]+", normalize(source_text)))
    source_stems = {token[:6] for token in source_tokens if len(token) >= 6}
    suggestion_tokens = [token for token in re.findall(r"[a-z0-9]+", normalize(value)) if len(token) >= 5]
    stopwords = {"sobre", "depois", "agora", "brasil", "verdade", "precisa", "explica", "debate", "rumo"}
    meaningful = [token for token in suggestion_tokens if token not in stopwords]
    shared = {
        token for token in meaningful
        if token in source_tokens or (len(token) >= 6 and token[:6] in source_stems)
    }
    return len(shared) >= 2


def _merge_ai_suggestions(
    base: dict[str, Any],
    payload: dict[str, Any],
    source_text: str = "",
    preferred_format: str = "auto",
) -> dict[str, Any]:
    """Accept only short, evidence-backed AI variations; deterministic safety stays intact."""
    suggested = payload.get("formats") if isinstance(payload, dict) else None
    if not isinstance(suggested, dict):
        return base
    allowed_formats = (preferred_format,) if preferred_format in FORMAT_IDS else (FORMAT_VERTICAL, FORMAT_SQUARE)
    for format_id in allowed_formats:
        variants = suggested.get(format_id)
        if not isinstance(variants, list):
            continue
        accepted = []
        for item in variants[:3]:
            if not isinstance(item, dict):
                continue
            headline = _compact(str(item.get("headline", "")), FORMAT_PROFILES[format_id]["headline_limit"])
            eyebrow = _compact(str(item.get("eyebrow", "")), FORMAT_PROFILES[format_id]["eyebrow_limit"])
            if len(headline.split()) < 2:
                continue
            profile = FORMAT_PROFILES[format_id]
            if source_text and not _suggestion_has_evidence(headline, source_text):
                continue
            normalized_headline = headline.upper()
            accepted.append({
                "eyebrow": eyebrow.upper(),
                "headline": normalized_headline,
                "headline_lines": _break_headline(
                    normalized_headline,
                    max_lines=int(profile.get("max_lines", 3)),
                    ideal_line_chars=int(profile.get("ideal_line_chars", 22)),
                ),
                "emphasis": _compact(str(item.get("emphasis", "")), 18).upper(),
                "accent": "red_on_white" if item.get("accent") == "red_on_white" else "white",
                "character_count": len(headline),
                "word_count": len(headline.split()),
                "layout_hint": f"até {profile.get('max_lines', 3)} linhas de cerca de {profile.get('ideal_line_chars', 22)} caracteres",
            })
        if accepted:
            base["formats"][format_id]["suggestions"] = accepted
    tweets = suggested.get(FORMAT_TWEET) if preferred_format in {"auto", FORMAT_TWEET} else None
    if isinstance(tweets, list):
        accepted_tweets = []
        for item in tweets[:2]:
            text = _compact(str(item.get("post_text", "")), FORMAT_PROFILES[FORMAT_TWEET]["headline_limit"])
            if len(text.split()) >= 4 and (not source_text or _suggestion_has_evidence(text, source_text)):
                accepted_tweets.append({
                    "post_text": text,
                    "character_count": len(text),
                    "attribution_note": "Rascunho de publicação: revise a atribuição e a redação antes de usar o perfil.",
                })
        if accepted_tweets:
            base["formats"][FORMAT_TWEET]["suggestions"] = accepted_tweets
    requested = payload.get("recommended_format")
    if requested in FORMAT_IDS:
        base["recommended_format"] = requested
    if isinstance(payload.get("recommendation_reason"), str):
        base["recommendation_reason"] = _compact(payload["recommendation_reason"], 220)
    base["generation_source"] = "ai_refined"
    return base


def detect_artwork_topic(transcript: str) -> str:
    """Return the evidenced topic used to scope local headline learning."""
    text, _metadata = _coerce_text(transcript)
    return _topic(text)


def generate_artwork_copy(
    transcript: str,
    mini_context: str = "",
    preferred_format: str = "auto",
    ai_backend: Any | None = None,
    emit_progress=None,
    editorial_learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate short, format-aware artwork copy from a finished-cut transcript."""
    text, transcript_meta = _coerce_text(transcript)
    context = _compact(mini_context, 280)
    preferred = preferred_format if preferred_format in FORMAT_IDS else "auto"
    result = _fallback_result(text, context, preferred, editorial_learning=editorial_learning)
    basis = result.setdefault("analysis", {}).setdefault("headline_basis", {})
    basis.update({
        "topic": result.get("topic", "geral"),
        "evidence_terms": list(result.get("topic_evidence") or [])[:8],
        "grounded_claims": [
            str(item) for item in _claim_candidates(text, result.get("topic", "política"), speaker_prefix="")[:6]
            if str(item).strip()
        ],
        "instruction": "Use somente a legenda e o minic contexto; não invente fatos, números, intenção ou acusação.",
    })
    result["transcript"] = {
        **transcript_meta,
        "word_count": len(text.split()),
        "excerpt": _compact(text, 280),
    }
    result["mini_context"] = context

    if ai_backend is not None:
        if emit_progress:
            emit_progress("[Texto de arte] Refinando opções curtas pelo modo de IA configurado...", "info")
        attribution_rule = (
            "Só use 'RENAN:' ou 'RENAN CRITICA' se a transcrição ou o minic contexto identificar explicitamente Renan; caso contrário, não atribua a fala a uma pessoa específica."
            if _speaker_prefix(context) or "renan" in normalize(text)
            else "Não atribua a fala a Renan nem a qualquer pessoa específica sem identificação explícita na transcrição ou no minic contexto."
        )
        system = f"""Você é editor de vídeos políticos curtos no Brasil. Gere texto de ARTE, não SEO.
Use somente ideias claramente presentes na transcrição. Intensifique o contraste sem inventar fatos, crimes, números, intenções ou acusações. {attribution_rule}
A resposta deve ser somente JSON válido. Para 1:1 e 9:16, headline é curta, em caixa alta e sem descrição complementar. Respeite rigorosamente os limites informados."""
        format_scope = preferred if preferred in FORMAT_IDS else "todos os três formatos para recomendação"
        basis_payload = (result.get("analysis") or {}).get("headline_basis") or {}
        prompt_text = text if len(text) <= 12000 else f"{text[:8000]}\n[trecho intermediário omitido]\n{text[-4000:]}"
        prompt = f"""FORMATO SOLICITADO: {format_scope}

BASE TEXTUAL OBRIGATÓRIA:
{json.dumps(basis_payload, ensure_ascii=False)}

TRANSCRIÇÃO COMPLETA OU TRECHOS INICIAL E FINAL DO CORTE:
{prompt_text}

MINICONTEXTO DO EDITOR:
{context or '(nenhum)'}

HISTÓRICO AGREGADO DE CORTES APROVADOS (use apenas como padrão, nunca copie texto e nunca substitua a transcrição):
{json.dumps((result.get('analysis') or {}).get('approved_clip_prior') or {}, ensure_ascii=False)}

Produza JSON neste formato:
{{
  "recommended_format": "vertical_916|square_alfinetei|fake_tweet",
  "recommendation_reason": "motivo breve",
  "formats": {{
    "vertical_916": [{{"eyebrow":"", "headline":"até 58 caracteres", "emphasis":"até 18 caracteres", "accent":"white|red_on_white"}}],
    "square_alfinetei": [{{"eyebrow":"até 18 caracteres", "headline":"até 64 caracteres", "emphasis":"", "accent":"white"}}],
    "fake_tweet": [{{"post_text":"até 180 caracteres"}}]
  }}
}}
Gere no máximo 3 alternativas por formato permitido. Se houver um formato solicitado, não gere alternativas para os demais."""
        try:
            refined = _extract_json(ai_backend.generate(prompt, system, emit_progress))
            if refined:
                result = _merge_ai_suggestions(result, refined, source_text=text, preferred_format=preferred)
        except Exception:
            # A deterministic, explainable output is preferable to a failed screen.
            pass
    result["generated_format"] = preferred if preferred in FORMAT_IDS else result.get("recommended_format", FORMAT_VERTICAL)
    return result
