"""Pure gates for clip boundaries, with no external dependencies.

Research basis:
- `pesquisa-fronteira-de-saida-do-corte-2026-09-02.md` (Chub, 16.871 blocos)
- `pesquisa-fronteira-de-entrada-2026-09-01.md` (fronteira de assunto)
"""

from __future__ import annotations

import re

_BACKCHANNELS = {
    "ta",
    "tá",
    "uhum",
    "e isso",
    "é isso",
    "obrigado",
    "perfeito",
    "certo",
    "exato",
    "isso",
    "é",
    "sim",
    "não",
    "nao",
    "né",
    "aham",
    "show",
    "demais",
    "valeu",
}

_DEPENDENT_CONNECTIVES = {
    "e",
    "mas",
    "então",
    "aí",
    "ai",
    "pois",
    "porque",
    "que",
    "né",
    "certo",
    "é",
    "tá",
    "ta",
    "ah",
    "eh",
    "ih",
    "também",
    "tbm",
    "assim",
    "logo",
    "portanto",
    "contudo",
    "todavia",
    # Adicionados 2026-09-03 a partir dos cortes reprovados pelo editor
    # (Flow News #065): abriram argumento pendurado no que veio antes.
    # NÃO incluir palavras que abrem tese sozinhas ("agora", "no", "por"):
    # medido, elas derrubam abertura legítima.
    "tipo",
    "só",
    "so",
    "daí",
    "dai",
    "enfim",
    "inclusive",
    "aliás",
    "alias",
    "ou",
    "porém",
    "porem",
    "entretanto",
}

# Anáfora: pronome/demonstrativo que aponta para fora do corte.
# Só entram os que NÃO conseguem se resolver sozinhos. "isso"/"isto" ficam
# de fora: em fala corrente eles quase sempre apontam para a própria frase
# ("ninguém aguenta mais isso"), e incluí-los reprova abertura boa.
_ANAFORAS = {
    "ele", "ela", "eles", "elas",
    "dele", "dela", "deles", "delas",
    "nele", "nela", "neles", "nelas",
    "aquilo",
    "nesse", "nessa", "nesses", "nessas",
    "naquele", "naquela",
    "desse", "dessa", "desses", "dessas",
    "daquele", "daquela",
    "lhe", "lhes",
}

# Quantas palavras da abertura são inspecionadas em busca de anáfora órfã.
_ANAFORA_JANELA_PALAVRAS = 15

# Abaixo disto o clipe inteiro é um toco (artefato de truncagem), não uma
# abertura editorial curta. "Agora vai começar." tem 3 palavras e é uma frase
# inteira; "Mas..." e "E aí?" têm 1-2 e não abrem nada.
_TOCO_MAX_PALAVRAS = 3


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _primeira_frase(texto: str) -> str:
    """A janela de abertura: a primeira frase, ou o começo se não houver ponto.

    Os gates julgam a BORDA do corte, não o corte inteiro. Receber o clipe
    completo e medir seu tamanho foi o defeito que manteve os dois gates
    mudos em 86 de 86 cortes (medido 2026-09-03).
    """
    partes = re.split(r"(?<=[.!?])\s+", texto, maxsplit=1)
    return partes[0] if partes else texto


def _ultima_frase(texto: str) -> str:
    """A janela de fecho: a última frase do corte."""
    partes = [p for p in re.split(r"(?<=[.!?])\s+", texto) if p.strip()]
    return partes[-1] if partes else texto


def fim_fragmentado(text: str, *, min_chars: int = 15) -> bool:
    """Return True if the clip ENDING looks like a truncated fragment.

    Judges the last sentence, not the whole clip. A backchannel or legitimate
    closing phrase is not a fragment, even when short. Research shows short
    non-backchannel endings are 3,6x less likely to become excellence clips
    and 2,15x more likely to be bad clips.
    """
    normalized = _clean(text)
    if not normalized:
        return False
    janela = _clean(_ultima_frase(normalized))
    if not janela:
        return False
    despido = janela.lower().strip(".,;:!?…–—")
    if despido in _BACKCHANNELS:
        return False
    return len(despido) < min_chars


def abre_dependente(text: str, *, min_chars: int = 25) -> bool:
    """Return True if the clip OPENING depends on prior context.

    Judges the first sentence, not the whole clip.

    Two independent signals, either one is enough:

    1. Discourse connective opening the sentence. "Ah, mas...", "Tipo,...",
       "Só só assim..." continue an argument that stayed behind, regardless
       of how long the sentence is.

    2. Orphan anaphora: a pronoun in the opening window with no concrete
       antecedent (proper noun) before it inside the clip. "eles vão lá",
       "por ele" — the viewer cannot resolve the reference from the clip.

    ``min_chars`` only applies to a clip whose ENTIRE text is a stub — fewer
    than ``_TOCO_MAX_PALAVRAS`` words AND shorter than ``min_chars`` — which is
    a truncation artifact rather than an editorial opening. A short but whole
    sentence ("O governo errou de novo.", 24 chars, 5 words) opens fine.
    Measuring the first sentence against this ceiling was a bug that reproved
    good openings (2026-09-03).
    """
    normalized = _clean(text)
    if not normalized:
        return False

    janela = _clean(_primeira_frase(normalized))
    if not janela:
        return False

    palavras = janela.split()
    first_word = palavras[0].lower().strip(".,;:!?…–—")

    # Sinal 1: conectivo de discurso na abertura. Sem teto de tamanho.
    if first_word in _DEPENDENT_CONNECTIVES:
        return True

    # Sinal 2: anáfora órfã nas primeiras palavras da abertura.
    cabeca = palavras[:_ANAFORA_JANELA_PALAVRAS]
    for posicao, bruta in enumerate(cabeca):
        limpa = bruta.lower().strip(".,;:!?…–—\"'()")
        if limpa not in _ANAFORAS:
            continue
        # Nome próprio antes da anáfora (fora da 1ª palavra, que é maiúscula
        # por ser início de frase) resolve a referência dentro do corte.
        anterior = cabeca[:posicao]
        tem_antecedente = any(
            p[:1].isupper() and p.lower().strip(".,;:!?…–—") not in _ANAFORAS
            for p in anterior[1:]
        )
        if not tem_antecedente:
            return True

    # Clipe inteiro é um toco: poucas palavras E curto. Artefato de truncagem,
    # não abertura editorial.
    todas = normalized.split()
    return len(todas) < _TOCO_MAX_PALAVRAS and len(normalized) < min_chars
