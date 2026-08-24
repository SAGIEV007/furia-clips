"""A headline como o editor a escreve: gancho, frase e um trecho em destaque.

A forma sai da arte que ele produziu e aprovou:

    BOMBA!
    Presidenciável Renan Santos critica a [COMPRA DE VOTOS] desenfreada no país.

Três coisas que o gerador anterior não tinha e que ele apontou uma a uma:

1. **O gancho não é opcional.** As três headlines que saíram sem ele foram
   reprovadas por isso antes de qualquer outra coisa. Aqui toda variação sai com
   um, e um tom neutro escolhe o gancho brando — nunca nenhum.

2. **A frase não é citação, é leitura.** "as legendas podem ser também uma
   interpretação; mesmo parafraseando não precisa ser literal, tem apenas que
   fazer sentido." Isso não conflita com o invariante do NORTE, que é sobre
   **aspas**: sem aspas não há promessa de literalidade a quebrar. A regra que
   fica é a fronteira entre os dois modos — `resumo` sai sem aspas e pode
   parafrasear; `citacao` sai com aspas e continua literal palavra por palavra.

3. **A legenda pode errar; a headline não pode.** Por isso a fala é limpa antes
   de virar arte: falso começo, gagueira de reconhecimento e muleta de conversa
   saem. Limpar era proibido enquanto tudo era citação; no modo resumo é
   obrigatório, porque "tá presente" e "é você tá na base do prefeito ajuda isso"
   não são frases que alguém publica.

O que continua valendo sem exceção: nada entra na headline que não esteja na
fonte. Parafrasear é dizer com outras palavras o que foi dito, não acrescentar o
que não foi.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .headline_quote import (
    _ATTACK,
    _COMMITMENT,
    _FUNCTION_WORDS,
    _REFUSAL,
    Speaker,
)
from .political_profile import normalize


# Os ganchos que o editor usa, por tom, do mais forte para o mais brando. O
# primeiro de cada família é o padrão e os outros ficam à mão para ele trocar
# sem reescrever a headline inteira.
# As chamadas superiores saem do feed do editor, não da minha cabeça. Eram treze
# ganchos inventados aqui contra dezenove que ele publicou de verdade, e só
# "BOMBA!" coincidia — que é exatamente a queixa dele sobre as headlines que
# rejeitou: "não tem uma coisa para chamar a atenção como eu fiz no meu".
#
# `estilo_publicado.ganchos_que_transferem()` já removeu as que não servem a
# outro corte: as que nomeiam gente ("FIM DO XANDÃO?") e as que afirmam algo
# sobre o próprio corte ("VIRALIZOU!" num corte que nem foi publicado). O que
# resta é reação pura, e a postura só escolhe qual delas cabe.
_POSTURA_DO_GANCHO = {
    "denuncia": ("BOMBA!", "NA LATA!", "SEM FILTRO!", "CHOCADA!", "MEU DEUS!"),
    "alerta": ("MEU DEUS!", "BOMBA!", "ANOTOU A PLACA?", "CHOCADA!"),
    "promessa": ("ANOTOU A PLACA?", "IMPRESSIONANTE", "SIM!!", "DESAFIO!"),
    "neutro": ("IMPRESSIONANTE", "INUSITADO!", "INCRÍVEL:", "ANOTOU A PLACA?"),
}


def _hooks_do_feed():
    """A escolha por postura, filtrada pelo que o feed realmente tem.

    Se o corpus de estilo mudar — ele é transcrito à mão de capturas de tela —
    uma chamada que sumir de lá some daqui, em vez de continuar viva numa
    constante que ninguém revisa.
    """
    from .estilo_publicado import ganchos_que_transferem

    disponiveis = set(ganchos_que_transferem())
    escolhidos = {}
    for postura, preferidos in _POSTURA_DO_GANCHO.items():
        mantidos = tuple(g for g in preferidos if g in disponiveis)
        escolhidos[postura] = mantidos or tuple(sorted(disponiveis))[:3] or ("BOMBA!",)
    return escolhidos


HOOKS = _hooks_do_feed()

# O verbo diz a postura, e ela tem de estar no texto. "critica" e "denuncia" são
# afirmações sobre o que a pessoa fez; usá-los sem evidência é editorializar por
# conta própria, e é o mesmo erro de atribuir fala por palpite.
STANCE_VERBS = {
    "denuncia": ("critica", "denuncia", "expõe"),
    "alerta": ("alerta sobre", "critica"),
    "promessa": ("promete acabar com", "quer enfrentar"),
    "neutro": ("fala sobre", "explica"),
}

# Papéis que o editor usa para nomear o entrevistado na terceira pessoa. Só
# entram com evidência no contexto: chamar alguém de presidenciável quando ele
# não é candidato é inventar um fato na headline.
_ROLE_EVIDENCE = (
    ("Presidenciável", ("presidencia", "presidente da republica", "presidenciavel", "candidato a presidencia")),
    ("Candidato", ("candidato", "candidatura", "eleicao", "eleicoes", "campanha")),
    ("Deputado", ("deputado",)),
)

# Muletas de conversa. No modo resumo elas saem, porque ninguém publica "tipo",
# "né" e "vamos dizer" numa arte.
_FILLERS = (
    "né", "ne", "tipo", "assim", "sabe", "entendeu", "digamos", "vamos dizer",
    "quer dizer", "enfim", "ó", "pô", "cara", "eh", "ah", "hein", "olha só",
    "por assim dizer", "no fundo", "veja bem", "vamos supor", "vamos falar",
)

# Começos que são falso arranque, não começo de frase.
_FALSE_STARTS = (
    "é", "eh", "ah", "ó", "pô", "e", "mas", "então", "entao", "aí", "ai", "que",
    "porque", "ou seja", "olha", "veja", "bom", "beleza", "tá", "ta", "né", "ne",
)

_STUTTER = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)

# Fala corrente vira arte em registro escrito. Isso é reescrita, e só é legítimo
# no modo resumo — numa citação com aspas seria falsificar o que a pessoa disse.
_CONTRACTIONS = (
    (r"\btá\b", "está"), (r"\btão\b", "estão"), (r"\btô\b", "estou"),
    (r"\btava\b", "estava"), (r"\btavam\b", "estavam"),
    (r"\bpra\b", "para"), (r"\bpro\b", "para o"), (r"\bcê\b", "você"),
    (r"\bnum\b", "não"), (r"\bpr'a\b", "para"),
)

# "eu acho que o STF está uma porcaria" — o que vira headline é o que vem depois
# do "acho que". A moldura de opinião é do falante, não da afirmação.
_OPINION_FRAME = re.compile(
    r"^\s*(?:tenho\s+)?(?:eu\s+)?(?:acho|penso|diria|acredito|entendo|considero)\s+que\s+",
    re.IGNORECASE,
)

# Uma headline lida de uma vez. O NORTE mediu que curto vence: da faixa mais
# curta para a mais longa a mediana de views cai 36%. Aqui isso ordena e limita,
# nunca recusa.
HEADLINE_IDEAL_CHARS = 72
HEADLINE_MAX_CHARS = 110
SPAN_MIN_WORDS = 5
SPAN_MAX_WORDS = 16


@dataclass(frozen=True)
class Headline:
    hook: str
    text: str
    emphasis: str
    mode: str
    hook_alternatives: tuple[str, ...] = ()
    start_s: float | None = None
    end_s: float | None = None
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "hook": self.hook,
            "hook_alternatives": list(self.hook_alternatives),
            "text": self.text,
            "emphasis": self.emphasis,
            "mode": self.mode,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "character_count": len(self.text),
            "word_count": len(self.text.split()),
        }


# ── limpeza ────────────────────────────────────────────────────────────────

def clean_for_artwork(text: str) -> str:
    """A fala sem o ruído que ninguém publica.

    Não inventa nem troca palavra por sinônimo: remove repetição de
    reconhecimento, muleta de conversa e falso arranque, e devolve o resto com
    inicial maiúscula e ponto final. É paráfrase por subtração, que é a mais
    segura que existe — tudo o que sobra foi dito.
    """
    limpo = " ".join(str(text or "").split())
    if not limpo:
        return ""

    limpo = _STUTTER.sub(r"\1", limpo)
    for padrao, escrito in _CONTRACTIONS:
        limpo = re.sub(padrao, escrito, limpo, flags=re.IGNORECASE)
    for muleta in sorted(_FILLERS, key=len, reverse=True):
        limpo = re.sub(rf"(?<!\w){re.escape(muleta)}(?!\w)[,\s]*", " ", limpo, flags=re.IGNORECASE)
    limpo = " ".join(limpo.split())

    # Falso arranque: até três palavras de abertura que não abrem nada.
    for _ in range(3):
        palavras = limpo.split()
        if len(palavras) < 2:
            break
        if normalize(palavras[0]).strip() in _FALSE_STARTS:
            limpo = " ".join(palavras[1:])
        else:
            break

    limpo = limpo.strip(" ,;:-—–")
    if not limpo:
        return ""
    # Cauda pendurada: uma headline não termina em conjunção.
    palavras = limpo.split()
    while palavras and normalize(palavras[-1]) in _FUNCTION_WORDS:
        palavras.pop()
    limpo = " ".join(palavras).strip(" ,;:-—–")
    if not limpo:
        return ""

    limpo = limpo[0].upper() + limpo[1:]
    if not limpo.endswith((".", "!", "?")):
        limpo += "."
    return limpo


# ── o termo que vai em destaque ────────────────────────────────────────────

_ARTICLES = {"o", "a", "os", "as"}

# Verbos conjugados que abrem uma oração sem sujeito. Depois de "Fulano diz que"
# elas ficam penduradas — "diz que estão envolvido em escândalo" não diz quem.
_SUBJECTLESS_VERB_START = {
    "esta", "estao", "estou", "estamos", "tem", "temos", "tinha", "vai", "vou",
    "vamos", "sao", "foi", "foram", "era", "eram", "fica", "ficam", "custa",
    "custam", "passa", "passam", "precisa", "precisam", "quer", "querem", "faz",
    "fazem", "diz", "dizem", "sabe", "sabem", "parece", "parecem", "continua",
    "continuam", "chega", "chegam", "entra", "entram", "pode", "podem", "deve",
}


def key_term(texts: list[str]) -> tuple[str, str]:
    """O assunto da fonte, na forma em que ele foi dito, e o artigo que o rege.

    É o trecho que vai destacado na arte, e por isso não pode ser escolhido por
    tema abstrato: "COMPRA DE VOTOS" é o que o editor destacou porque é o que a
    fonte repete. Sai da contagem de expressões de duas a quatro palavras que
    começam e terminam em palavra de conteúdo.

    O artigo vem junto e vem **da fonte**, não de uma regra de gênero que eu não
    tenho como aplicar: sem ele o molde escreveu "alerta sobre a ESTADOS UNIDOS".
    Se a fonte nunca antecede a expressão de artigo, o molde sai sem artigo em
    vez de chutar um.
    """
    bruto = " ".join(t for t in texts if t)
    palavras = re.findall(r"[\wÀ-ÿ]+", bruto.lower())
    if len(palavras) < 8:
        return "", ""

    ocorrencias: Counter[str] = Counter()
    artigos: dict[str, Counter[str]] = {}

    # Uma sigla é candidata sozinha. "STF", "PCC", "INSS" são exatamente o que o
    # editor destaca, e o contador de expressões nunca as via: ele só montava
    # gramas de duas a quatro palavras, e sigla tem uma. Num corte de dezoito
    # segundos sobre o STF isso significou nenhum assunto e nenhuma headline.
    siglas = {s.lower() for s in re.findall(r"\b[A-ZÀ-Þ]{2,6}\b", bruto)}
    for posicao, palavra in enumerate(palavras):
        if palavra in siglas:
            ocorrencias[palavra] += 1
            anterior = palavras[posicao - 1] if posicao else ""
            if anterior in _ARTICLES:
                artigos.setdefault(palavra, Counter())[anterior] += 1

    for tamanho in (2, 3, 4):
        for i in range(len(palavras) - tamanho + 1):
            grama = palavras[i:i + tamanho]
            if normalize(grama[0]) in _FUNCTION_WORDS or normalize(grama[-1]) in _FUNCTION_WORDS:
                continue
            if sum(1 for p in grama if normalize(p) not in _FUNCTION_WORDS) < 2:
                continue
            chave = " ".join(grama)
            ocorrencias[chave] += 1
            anterior = palavras[i - 1] if i else ""
            if anterior in _ARTICLES:
                artigos.setdefault(chave, Counter())[anterior] += 1
    if not ocorrencias:
        return "", ""

    # Repetição é o que faz de uma expressão o assunto da fonte; o comprimento só
    # desempata. Antes o critério era peso — ocorrências vezes o tamanho do grama
    # — e isso exigia de uma fonte de setenta palavras a mesma repetição que uma
    # de mil, o que na prática recusava todo corte curto.
    # A repetição é o filtro, e ela vem antes do desempate — aplicá-la só ao
    # vencedor deixava um grama de quatro palavras visto uma única vez ganhar de
    # "STF" visto duas, e então cair no filtro levando o assunto junto.
    repetidos = {termo: vezes for termo, vezes in ocorrencias.items() if vezes >= 2}
    if not repetidos:
        return "", ""

    def valor(item: tuple[str, int]) -> tuple[float, int]:
        expressao, vezes = item
        return (vezes * (1 + 0.4 * (len(expressao.split()) - 1)), len(expressao))

    melhor, _ = max(repetidos.items(), key=valor)
    regente = artigos.get(melhor)
    return melhor.upper(), (regente.most_common(1)[0][0] if regente else "")


# ── postura e papel ────────────────────────────────────────────────────────

def detect_stance(text: str, signals: dict[str, Any] | None = None) -> str:
    """Que postura o trecho sustenta. O verbo da headline sai daqui."""
    folded = normalize(text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    conflito = float((signals or {}).get("conflict_or_stakes", 0) or 0)

    if tokens & _ATTACK or conflito >= 55:
        return "denuncia"
    if _COMMITMENT.search(folded) or _REFUSAL.search(folded):
        return "promessa"
    if conflito >= 35:
        return "alerta"
    return "neutro"


def detect_role(mini_context: str, text: str) -> str:
    """"Presidenciável" só quando a fonte ou o editor disserem que ele é."""
    folded = normalize(f"{mini_context} {text}")
    for papel, marcas in _ROLE_EVIDENCE:
        if any(marca in folded for marca in marcas):
            return papel
    return ""


# ── as duas famílias de headline ───────────────────────────────────────────

def summary_headlines(
    speaker: Speaker, role: str, stance: str, termo: str, fonte: str, artigo: str = ""
) -> list[str]:
    """`Presidenciável Renan Santos critica a COMPRA DE VOTOS no Brasil.`

    A gramática vem do molde, não da fala. Essa escolha é deliberada e vale
    registrar por que: a primeira tentativa recortava uma janela de palavras da
    própria fala e a promovia a frase, e numa legenda sem pontuação isso produziu
    "Existe compra de voto é um quanto." — que não é frase nenhuma. Recortar fala
    não produz gramática. O molde produz, e os únicos campos variáveis são um
    nome e uma expressão que a fonte repete, ambos verificáveis.

    O preço é que o molde pode soar plano. Quem resolve isso é o caminho de IA,
    que agora pode reescrever de verdade porque não há aspas prometendo
    literalidade — e é por isso que ele deixou de ser opcional na tela.

    Sem alguém que responda por quem fala esta família não sai: ela nomeia a
    pessoa em terceira pessoa e afirma o que ela fez, e as duas coisas exigem
    quem.
    """
    if not speaker.confirmed or not termo:
        return []
    folded = normalize(fonte)
    verbo, alternativo = STANCE_VERBS[stance][0], STANCE_VERBS[stance][-1]
    sujeito = " ".join(part for part in (role, speaker.name) if part)

    alvo = f"{artigo} {termo}".strip()

    saidas = [f"{sujeito} {verbo} {alvo}."]
    # O lugar só entra com evidência: dizer "no Brasil" de uma fala que não fala
    # do Brasil é inventar um fato dentro da headline.
    if "brasil" in folded or "brasileir" in folded:
        saidas.append(f"{sujeito} {verbo} {alvo} no Brasil.")
    # E o "como funciona" só quando a fonte de fato explica um mecanismo.
    if any(marca in folded for marca in ("funciona assim", "mecanismo", "esquema", "como funciona")):
        saidas.append(f"{sujeito} explica como funciona {alvo} no Brasil.")
    elif alternativo != verbo:
        saidas.append(f"{sujeito} {alternativo} {alvo}.")
    return [" ".join(item.split()) for item in saidas]


def claim_headlines(units: list[dict[str, Any]], speaker: Speaker, termo: str) -> list[tuple[str, dict[str, Any]]]:
    """`Renan Santos diz que o STF está uma porcaria.`

    A família do assunto diz sobre *o que* ele falou; esta diz *o que ele disse*,
    e é a que carrega a força. Faltava, e por isso um corte de dezoito segundos
    sobre o STF — cuja frase mais forte estava inteira na fonte — não rendia
    headline nenhuma.

    A gramática continua vindo do molde: "Fulano diz que" é fixo, e o que entra
    depois é uma oração limpa da própria fala, sem a moldura de opinião do
    falante. Nada aqui recorta pelo meio; ou a unidade vira oração inteira, ou
    ela não entra.
    """
    if not speaker.confirmed:
        return []
    from .clip_selector import ClipSelector
    from .headline_quote import _disqualify, transcript_is_punctuated

    cased = ClipSelector._casing_is_meaningful(units)
    punctuated = transcript_is_punctuated(units)

    saidas: list[tuple[str, dict[str, Any]]] = []
    for unidade in units or []:
        bruto = str(unidade.get("text") or "")
        # Os mesmos portões de todo o resto. Sem esta linha a família nova
        # atribuiu ao entrevistado uma fala que ele estava *encenando* na voz de
        # um cabo eleitoral — a citação falsa mais cara que este módulo produz, e
        # que já tinha sido recusada uma vez por outro caminho.
        if _disqualify(bruto, cased, punctuated):
            continue
        limpo = clean_for_artwork(bruto).rstrip(".!?")
        limpo = _OPINION_FRAME.sub("", limpo).strip()
        if not limpo:
            continue
        palavras = limpo.split()
        if not (4 <= len(palavras) <= 16):
            continue
        primeira = normalize(palavras[0])
        if primeira in _FUNCTION_WORDS and primeira not in _ARTICLES:
            continue
        # "estão envolvido em escândalo…" é oração sem sujeito: depois de "diz
        # que" ela fica pendurada, e o molde só garante a gramática do que ele
        # próprio escreve.
        if primeira in _SUBJECTLESS_VERB_START:
            continue
        frase = f"{speaker.name} diz que {limpo[0].lower() + limpo[1:]}."
        if len(frase) > HEADLINE_MAX_CHARS:
            continue
        saidas.append((frase, unidade))
    # A afirmação que fala do assunto da fonte vem primeiro, e entre iguais a
    # mais curta — curto vence, medido no Campaign Hub.
    saidas.sort(key=lambda item: (
        0 if termo and normalize(termo) in normalize(item[0]) else 1, len(item[0])
    ))
    return saidas


# O verbo da atribuição, na forma que o editor usa na arte. Cada um afirma algo
# sobre *como* a pessoa falou, então cada um exige evidência no próprio trecho.
ATTRIBUTION_VERBS = {
    "denuncia": "DETONA",
    "promessa": "CRAVA",
    "alerta": "ALERTA",
    "neutro": "DIZ",
}


def attributed_headlines(
    units: list[dict[str, Any]], speaker: Speaker, termo: str, stance: str
) -> list[tuple[str, dict[str, Any]]]:
    """`RENAN SANTOS DETONA: "O STF ESTÁ UMA PORCARIA"`

    A forma da arte que o editor produziu e aprovou para este corte. Ela difere
    da família do resumo em duas coisas que importam: o verbo diz com que força
    ele falou, e a afirmação vai entre aspas.

    Sobre as aspas: elas carregam a afirmação como ela foi dita, passada para o
    registro escrito — "tá" vira "está", como o próprio editor escreveu na arte
    dele. Nenhuma palavra é acrescentada nem trocada por sinônimo. É a única
    flexibilização do invariante do NORTE nesta forma, ela é deliberada, e está
    registrada lá.
    """
    verbo = ATTRIBUTION_VERBS[stance]
    saidas = []
    for frase, unidade in claim_headlines(units, speaker, termo):
        afirmacao = frase.split(" diz que ", 1)[-1].rstrip(".")
        if not afirmacao:
            continue
        texto = f"{speaker.name} {verbo}: “{afirmacao}”".upper()
        if len(texto) > HEADLINE_MAX_CHARS:
            continue
        saidas.append((texto, unidade))
    return saidas


def apply_emphasis(texto: str, termo: str) -> str:
    """O trecho destacado, se ele estiver mesmo na headline."""
    if not termo:
        return ""
    if normalize(termo) in normalize(texto):
        return termo.upper()
    return ""


def build(
    units: list[dict[str, Any]],
    speaker: Speaker,
    mini_context: str = "",
    signals: dict[str, Any] | None = None,
    wanted: int = 3,
) -> list[Headline]:
    """As variações de headline para o editor escolher, com gancho em todas."""
    textos = [str(item.get("text") or "") for item in units or []]
    if not textos:
        return []
    from .headline_quote import pick_quotes
    from .interview_turns import is_interviewer_sentence
    from .clip_selector import ClipSelector

    inteiro = " ".join(textos)
    termo, artigo = key_term(textos)
    stance = detect_stance(inteiro, signals)
    role = detect_role(mini_context, inteiro)
    ganchos = HOOKS[stance]

    variacoes: list[Headline] = []

    for posicao, resumo in enumerate(summary_headlines(speaker, role, stance, termo, inteiro, artigo)):
        if len(resumo) > HEADLINE_MAX_CHARS:
            continue
        variacoes.append(Headline(
            hook=ganchos[0], text=resumo, emphasis=apply_emphasis(resumo, termo),
            mode="resumo", hook_alternatives=ganchos, score=100.0 - posicao,
        ))

    # A forma da arte aprovada vem primeiro: é a que o editor de fato publica.
    for frase, unidade in attributed_headlines(units, speaker, termo, stance)[:2]:
        variacoes.append(Headline(
            hook=ganchos[0], text=frase, emphasis=apply_emphasis(frase, termo),
            mode="atribuicao", hook_alternatives=ganchos,
            start_s=unidade.get("start"), end_s=unidade.get("end"),
            score=110.0 - max(0, len(frase) - HEADLINE_IDEAL_CHARS) * 0.3,
        ))

    # A afirmação vem logo depois do assunto e à frente da citação: ela diz o que
    # ele disse, que é o que o editor publica.
    for frase, unidade in claim_headlines(units, speaker, termo)[:2]:
        variacoes.append(Headline(
            hook=ganchos[0], text=frase, emphasis=apply_emphasis(frase, termo),
            mode="resumo", hook_alternatives=ganchos,
            start_s=unidade.get("start"), end_s=unidade.get("end"),
            score=95.0 - max(0, len(frase) - HEADLINE_IDEAL_CHARS) * 0.3,
        ))

    # Quando não há diarização, ainda assim é possível criar uma headline segura
    # baseada no trecho: ela sai sem nome e sem verbo de atribuição. O comportamento
    # anterior zerava a tela inteira porque as famílias ``summary`` e ``claim``
    # exigiam um locutor confirmado. Isso transformava uma legenda útil, como a de
    # uma live importada, em "nenhuma headline" mesmo quando havia afirmações fortes.
    # Aqui a unidade é apenas limpa por subtração (muletas, gagueira e arranque falso)
    # e permanece no contrato como ``resumo``. A ausência de locutor continua visível
    # em ``speaker_unconfirmed`` no estúdio, portanto não há atribuição silenciosa.
    from .headline_quote import _disqualify, transcript_is_punctuated
    cased = ClipSelector._casing_is_meaningful(units)
    has_pause_boundaries = any(
        str(item.get("boundary_source") or "") == "pausa" for item in units
    )
    punctuated = transcript_is_punctuated(units) and not has_pause_boundaries
    anonymous_units = pick_quotes(units, wanted=8, is_other_speaker=is_interviewer_sentence) if not punctuated else []
    for unidade in anonymous_units:
        bruto = str(unidade.text or "").strip()
        if _disqualify(bruto, cased, punctuated):
            continue
        limpo = clean_for_artwork(bruto).rstrip(".!?").strip()
        palavras = limpo.split()
        # Legendas sem pontuação podem formar unidades de até 24 palavras. Não
        # truncamos no meio de uma oração: aceitamos a unidade inteira quando ela
        # cabe no limite de caracteres da arte e deixamos o layout quebrá-la em linhas.
        if not (4 <= len(palavras) <= 24):
            continue
        frase = f"{limpo[0].upper() + limpo[1:]}."
        if len(frase) > HEADLINE_MAX_CHARS:
            continue
        variacoes.append(Headline(
            hook=ganchos[0], text=frase, emphasis=apply_emphasis(frase, termo),
            mode="resumo", hook_alternatives=ganchos,
            start_s=unidade.start_s, end_s=unidade.end_s,
            score=84.0 - max(0, len(frase) - HEADLINE_IDEAL_CHARS) * 0.3,
        ))

    # A citação literal continua existindo, e agora como o que ela sempre foi:
    # uma opção entre outras, com aspas. Ela passa pelos mesmos portões de
    # `pick_quotes` — fragmento, cortesia, fala encenada, legenda cortada — em
    # vez de um laço próprio: escrever a checagem duas vezes foi como
    # "cometimento de crime dentro daquela comunidade." voltou a sair com aspas
    # depois de já ter sido recusado uma vez.
    for citacao in pick_quotes(units, wanted=2, is_other_speaker=is_interviewer_sentence):
        if citacao.boundary_source != "pontuacao" or not citacao.verbatim:
            continue
        aspas = f"“{citacao.text}”"
        if len(aspas) > HEADLINE_MAX_CHARS:
            continue
        variacoes.append(Headline(
            hook=ganchos[0], text=aspas, emphasis=apply_emphasis(aspas, termo),
            mode="citacao", hook_alternatives=ganchos,
            start_s=citacao.start_s, end_s=citacao.end_s,
            score=70.0 - max(0, len(citacao.text) - HEADLINE_IDEAL_CHARS) * 0.3,
        ))

    variacoes.sort(key=lambda item: (-item.score, len(item.text)))

    # O nome de quem fala está em toda headline e por isso não distingue nenhuma.
    # Deixá-lo na assinatura fazia "Renan Santos" sozinho valer dois terços da
    # sobreposição, e a melhor variação do corte sobre o STF era descartada como
    # repetição da mais fraca.
    do_nome = {t for t in re.findall(r"[a-z0-9]+", normalize(speaker.name)) if len(t) >= 5}

    escolhidas: list[Headline] = []
    vistas: list[set[str]] = []
    for candidata in variacoes:
        assinatura = {
            t for t in re.findall(r"[a-z0-9]+", normalize(candidata.text))
            if len(t) >= 5 and t not in do_nome
        }
        if any(assinatura and len(assinatura & anterior) / len(assinatura) > 0.6 for anterior in vistas):
            continue
        escolhidas.append(candidata)
        vistas.append(assinatura)
        if len(escolhidas) >= max(1, wanted):
            break
    return escolhidas
