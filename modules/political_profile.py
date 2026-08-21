"""Editorial profile for political short-form clips.

The profile is intentionally explainable: it does not infer truth or political
bias. It measures whether a transcript segment has the narrative ingredients
that make a political clip self-contained and editable for short-form video.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict


PROFILE_NAME = "renan_santos_politics"

TOPIC_TERMS = {
    "politica", "governo", "presidente", "presidencia", "partido", "eleicao",
    "eleitoral", "campanha", "congresso", "senado", "camara", "deputado",
    "senador", "ministro", "stf", "supremo", "moraes", "lula", "bolsonaro",
    "mbl", "missao", "brasil", "estado", "prefeito", "governador", "lei",
    "ordem", "justica", "seguranca", "crime", "homicidio", "economia",
    "imposto", "tributo", "orcamento", "educacao", "saude", "liberdade",
    "corrupcao", "democracia", "constitucional", "proposta", "politico",
    "livro amarelo", "ideologia", "direita", "esquerda", "reforma", "desfavelizacao",
    "favela", "moradia", "pcc", "faccao", "milicia", "interior",
}

CLAIM_CUES = {
    "a verdade", "o problema", "a questao", "eu defendo", "eu proponho",
    "a minha proposta", "vamos", "precisamos", "o brasil precisa", "nao se pode",
    "isso significa", "o fato e", "o ponto e", "fica claro", "eu vou",
    "se eu for eleito", "quando eu for presidente", "a solucao",
    "pra resumir", "em resumo", "o que acontece e", "no final das contas",
}

CONFLICT_CUES = {
    "absurdo", "vergonha", "mentira", "ilegal", "ilegalmente", "corrupcao",
    "criminoso", "covarde", "traidor", "hipocrita", "ridiculo", "escandalo",
    "confronto", "bater", "enfrentar", "contra", "nao aceito", "nao se cumpre",
    "nao vai", "nunca", "jamais", "culpa", "fracasso", "perdeu", "enganou",
    "urgente", "chocante", "denuncia", "exposto", "desmascarado",
    "guerra", "punicao", "cadeia", "fuzil", "bola de ferro", "incompetente",
}

PROPOSAL_CUES = {
    "proponho", "proposta", "vamos criar", "vamos acabar", "vamos reduzir",
    "vamos aumentar", "vamos fazer", "meu plano", "a medida", "a solucao",
    "se eleito", "governo", "meta", "objetivo", "pretendo", "precisamos criar",
}

EVIDENCE_CUES = {
    "dados", "pesquisa", "numero", "numeros", "por cento", "percentual",
    "segundo", "relatorio", "estudo", "lei", "artigo", "constituicao",
    "documento", "fato", "historico", "exemplo", "caso", "estatistica",
}

UNRESOLVED_OPENERS = {
    "isso", "isto", "aquilo", "ele", "ela", "eles", "elas", "esse", "essa",
    "esses", "essas", "aquele", "aquela", "tambem", "como eu disse",
}

MOBILIZATION_CUES = {
    "compartilhe", "siga", "ajude", "participe", "doe", "vaquinha", "apoie",
    "vamos pra cima", "junte-se", "inscreva-se", "espalhe", "mostre",
}

SENSITIVE_ALLEGATION_CUES = {
    "corrupcao", "corrupto", "corrupta", "rachadinha", "lavagem de dinheiro",
    "desviou", "desvio de dinheiro", "suborno", "crime", "criminoso", "faccao",
    "faccoes", "milicia", "trafico", "calunia", "difamacao", "perseguicao",
    "perseguido", "ligacao com faccao", "cometeu crime", "roubou",
}

HUMOR_CUES = {
    "kkkk", "haha", "hahaha", "la ele", "piada", "meme", "risada", "coringou",
    "brincadeira", "zoeira", "comedia", "engracado", "engracada", "ironico", "ironia",
}

REACTION_CUES = {
    "reagiu", "reacao", "reagindo", "indignado", "indignada", "surpreendeu", "surpresa",
    "chocado", "chocante", "viralizou", "bateu", "questionado", "respondeu", "resposta",
    "ninguem esperava", "mudou de ideia", "mandou a real",
}

BACKSTAGE_CUES = {
    "bastidor", "bastidores", "por tras", "antes da live", "depois da live", "ao vivo",
    "live", "entrevista", "conversa", "familia", "irma", "mae", "pai", "viagem", "equipe",
}

CASUAL_CUES = {
    "comida", "supermercado", "bolo", "jogo", "jogando", "passeio", "dia a dia", "rotina",
    "curiosidade", "voce sabia", "bora", "la ele", "kkkk", "haha", "brincadeira", "zoeira",
}

TYPE_LABELS = {
    "confronto": "confronto/reacao",
    "proposta": "proposta/programa",
    "evidencia": "dado/denuncia",
    "mobilizacao": "mobilizacao",
    "discurso": "discurso/posicionamento",
}


def normalize(text: str) -> str:
    raw = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(char for char in raw if not unicodedata.combining(char))


def _count_cues(text: str, cues: set[str]) -> int:
    return sum(1 for cue in cues if cue in text)


def _score(base: float, hits: int, step: float, cap: float = 100.0) -> float:
    return max(0.0, min(cap, base + hits * step))


def _editorial_family(normalized: str, topic_hits: int, conflict_hits: int, proposal_hits: int, evidence_hits: int, questions: int, exclamations: int) -> tuple[str, float, dict[str, int]]:
    """Classify the dominant format without forcing every clip into politics."""
    humor_hits = _count_cues(normalized, HUMOR_CUES)
    reaction_hits = _count_cues(normalized, REACTION_CUES)
    backstage_hits = _count_cues(normalized, BACKSTAGE_CUES)
    casual_hits = _count_cues(normalized, CASUAL_CUES)
    political_hits = topic_hits + conflict_hits + proposal_hits + evidence_hits
    candidates = {
        "humor": humor_hits * 3 + (2 if exclamations >= 2 else 0),
        "reacao": reaction_hits * 2 + (1 if questions or exclamations else 0),
        "bastidor": backstage_hits * 2,
        "descontraido": casual_hits * 2,
        "politico": political_hits,
    }
    family, raw_score = max(candidates.items(), key=lambda pair: pair[1])
    if raw_score <= 0:
        family = "conversa"
        raw_score = 1
    fit = min(100.0, 42.0 + raw_score * 11.0)
    return family, round(fit, 1), {
        "politico": political_hits,
        "humor": humor_hits,
        "reacao": reaction_hits,
        "bastidor": backstage_hits,
        "descontraido": casual_hits,
    }


def analyze_political_text(text: str, user_context: str = "", channel_context: str = "") -> Dict:
    """Return transparent political-editorial signals for one candidate clip."""
    raw = str(text or "")
    normalized = normalize(raw)
    words = normalized.split()
    word_count = len(words)
    topic_hits = sum(1 for term in TOPIC_TERMS if re.search(rf"\b{re.escape(term)}\b", normalized))
    claim_hits = _count_cues(normalized, CLAIM_CUES)
    conflict_hits = _count_cues(normalized, CONFLICT_CUES)
    proposal_hits = _count_cues(normalized, PROPOSAL_CUES)
    evidence_hits = _count_cues(normalized, EVIDENCE_CUES)
    mobilization_hits = _count_cues(normalized, MOBILIZATION_CUES)
    numbers = len(re.findall(r"\b\d+(?:[.,]\d+)?\b|\bpor cento\b", normalized))
    questions = raw.count("?")
    exclamations = raw.count("!")
    sentence_count = max(1, len([part for part in re.split(r"[.!?]+", raw) if part.strip()]))
    sensitive_claim_hits = _count_cues(normalized, SENSITIVE_ALLEGATION_CUES)
    named_entities = re.findall(
        r"\b[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,}(?:\s+[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][\wÁÀÃÂÉÊÍÓÔÕÚÇ-]{2,})+\b",
        raw,
    )
    named_entity_count = len(set(named_entities))
    ends_complete = raw.rstrip().endswith((".", "!", "?"))
    opening = " ".join(words[:4])
    opening_is_unresolved = any(
        opening == cue or opening.startswith(cue + " ")
        for cue in UNRESOLVED_OPENERS
    )
    editorial_family, editorial_family_fit, family_cue_counts = _editorial_family(
        normalized, topic_hits, conflict_hits, proposal_hits, evidence_hits, questions, exclamations
    )

    requested_words = {
        word for word in normalize(user_context).split()
        if len(word) >= 4 and word not in {"quero", "encontre", "momentos", "cortes", "fale", "sobre", "onde", "esteja"}
    }
    context_matches = sum(1 for word in requested_words if word in normalized)
    semantic_context_matches = 0
    if any(word in requested_words for word in {"confronto", "confrontos", "critica", "reacao"}) and conflict_hits:
        semantic_context_matches += 1
    if any(word in requested_words for word in {"stf", "moraes", "juridica", "juridico", "lei", "constituicao"}) and (evidence_hits or "ilegal" in normalized):
        semantic_context_matches += 1
    total_context_matches = context_matches + semantic_context_matches
    context_match = 50.0 if not requested_words else min(100.0, 20.0 + (total_context_matches / len(requested_words)) * 80.0)

    channel_signal = normalize(channel_context)
    profile_fit = 58.0
    if channel_signal and ("polit" in channel_signal or "renan" in channel_signal or "mbl" in channel_signal):
        profile_fit = _score(35.0, topic_hits, 8.0)

    topic_relevance = _score(22.0, topic_hits, 15.0)
    claim_strength = _score(30.0, claim_hits, 13.0)
    conflict_or_stakes = _score(28.0, conflict_hits, 12.0)
    proposal_strength = _score(24.0, proposal_hits, 15.0)
    evidence_density = _score(28.0, evidence_hits + min(numbers, 3), 10.0)
    mobilization = _score(20.0, mobilization_hits, 18.0)
    specificity = min(100.0, 32.0 + min(35.0, numbers * 12.0) + min(25.0, topic_hits * 5.0) + (10.0 if word_count >= 35 else 0.0))
    conclusion = min(100.0, 35.0 + (30.0 if ends_complete else 0.0) + (20.0 if sentence_count >= 3 else 0.0) + (15.0 if word_count >= 24 else 0.0))
    context_completeness = 78.0
    if opening_is_unresolved:
        context_completeness -= 24.0
    if word_count < 14:
        context_completeness -= 12.0
    if topic_hits:
        context_completeness += 8.0
    if claim_hits or conflict_hits:
        context_completeness += 6.0
    context_completeness = max(0.0, min(100.0, context_completeness))

    scores = {
        "topic_relevance": round(topic_relevance, 1),
        "claim_strength": round(claim_strength, 1),
        "conflict_or_stakes": round(conflict_or_stakes, 1),
        "proposal_strength": round(proposal_strength, 1),
        "evidence_density": round(evidence_density, 1),
        "mobilization": round(mobilization, 1),
        "specificity": round(specificity, 1),
        "conclusion": round(conclusion, 1),
        "context_completeness": round(context_completeness, 1),
        "context_match": round(context_match, 1),
        "profile_fit": round(profile_fit, 1),
        "editorial_family_fit": editorial_family_fit,
        "sensitive_claim_hits": float(sensitive_claim_hits),
        "named_entity_count": float(named_entity_count),
        "needs_fact_review": bool(sensitive_claim_hits),
        "needs_legal_review": bool(sensitive_claim_hits and named_entity_count),
        "questions": float(questions),
        "exclamations": float(exclamations),
    }

    candidates = {
        "confronto": conflict_or_stakes,
        "proposta": proposal_strength,
        "evidencia": evidence_density,
        "mobilizacao": mobilization,
        "discurso": claim_strength,
    }
    # In political editing, an explicit accusation or legal confrontation is
    # a confrontation format even when the same sentence cites evidence.
    if conflict_hits and ("ilegal" in normalized or "nao se cumpre" in normalized or "nao aceito" in normalized):
        editorial_type = "confronto"
    else:
        editorial_type = max(candidates, key=candidates.get)
    if candidates[editorial_type] < 45:
        editorial_type = "discurso"

    scores["political_editorial_fit"] = round(
        0.20 * topic_relevance
        + 0.15 * claim_strength
        + 0.15 * conflict_or_stakes
        + 0.15 * proposal_strength
        + 0.12 * evidence_density
        + 0.08 * specificity
        + 0.09 * conclusion
        + 0.04 * context_match
        + 0.10 * context_completeness,
        1,
    )
    scores["editorial_type"] = TYPE_LABELS.get(editorial_type, editorial_type)
    scores["editorial_family"] = editorial_family
    scores["family_cue_counts"] = family_cue_counts
    scores["cue_counts"] = {
        "topic": topic_hits,
        "claims": claim_hits,
        "conflict": conflict_hits,
        "proposal": proposal_hits,
        "evidence": evidence_hits,
        "mobilization": mobilization_hits,
        "sensitive_claims": sensitive_claim_hits,
        "named_entities": named_entity_count,
    }
    return scores


def build_political_prompt_fragment() -> str:
    """Instruction block for LLM backends, grounded in the reference style."""
    return """PERFIL EDITORIAL: cortes políticos de alto contexto para vídeos curtos.
Priorize trechos que tenham uma tese, reação, humor ou conflito identificável nos primeiros segundos, desenvolvimento com posicionamento/proposta/dado/denúncia e uma conclusão clara. Classifique primeiro a família editorial dominante como politico, humor, reacao, bastidor, descontraido ou conversa; somente depois aplique o subtipo político confronto/reação, proposta/programa, dado/denúncia, discurso/posicionamento ou mobilização quando o conteúdo for de fato político. Inclua o setup necessário para o espectador entender quem está sendo criticado, qual é o assunto e qual é a consequência. Não invente fatos, não transforme opinião em fato e não atribua uma fala a um participante sem evidência na transcrição. Prefira cortes autossuficientes, com energia, especificidade e uma frase final forte; penalize abertura no meio da frase, pronomes sem antecedente, acusações sem contexto e encerramento antes da conclusão. Não force um momento de humor, reação ou bastidor a parecer um discurso político só porque o perfil do canal é político."""
