"""Escolher a frase que vira headline, e montá-la sem reescrever ninguém.

O `headline_studio` não gerava headline: era uma cadeia de condições fixas tiradas
de um vídeo sobre criptomoedas, e para qualquer fonte nova caía em `"A VERDADE
INCÔMODA SOBRE {TEMA}"`. Numa transcrição sobre cotas e ensino básico ele
respondeu `"O BRASIL QUER TRIBUTAR O PRÓPRIO FUTURO?"` — porque o trecho continha
a palavra "imposto" — e nada daquilo tinha sido dito.

A forma vem de uma headline que o editor produziu e aprovou, e tem três partes com
funções distintas:

    VERGONHA!
    RENAN SANTOS DETONA: "…"

- a **estampa** dá a emoção antes da leitura, e sai do tom medido do trecho;
- a **atribuição** diz quem fala e com que força, e segue o veredito de locutor;
- a **citação** é o conteúdo, e é **literal**.

O invariante que sustenta tudo: **a citação nunca é parafraseada.** Se a frase mais
forte não couber, corta-se pelo fim numa fronteira de oração, com reticências e com
o corte registrado — ou escolhe-se outra frase. Nunca se reescreve o que ele disse
para caber. Por isso a citação não passa pelo `_compact` do estúdio, que trunca no
meio de uma palavra: truncar uma citação é parafrasear sem dizer que parafraseou.

A atribuição nunca é chutada. Deduzir o locutor do próprio texto é exatamente o
erro que custa a conta, então o nome só entra quando alguém respondeu por ele — o
áudio ou o editor — e o verbo forte só quando o tom do trecho o justifica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .political_profile import normalize


# Quanto de citação cabe numa arte antes de ela deixar de ser lida. Não é um
# portão: o NORTE mede que headline curta vence, e mediu também que nada é
# recusado por ter 62 caracteres. Serve para ordenar, e como teto de segurança.
QUOTE_IDEAL_CHARS = 68
QUOTE_MAX_CHARS = 132
QUOTE_MIN_WORDS = 4
# Uma citação precisa afirmar alguma coisa. Medido nos oito cortes reais da
# entrevista do Metrópoles, a primeira versão deste gerador escolheu "Eu vou dar
# um exemplo." e "Seja muito bem-vindo." — curtas, em primeira pessoa, e sem
# conteúdo nenhum. Seis palavras e três palavras de conteúdo é o piso que separa
# uma afirmação de uma muleta de conversa.
# Cinco, e não seis, porque seis recusava a arte que o editor aprovou. A citação
# dela é "O STF ESTÁ UMA PORCARIA" — cinco palavras, três de conteúdo — e um piso
# que exclui o exemplo aceitável está calibrado contra o próprio editor. O que
# garante que cinco palavras dizem algo não é a contagem total e sim
# `HEADLINE_MIN_CONTENT_WORDS`, que continua em três.
HEADLINE_MIN_WORDS = 5
HEADLINE_MIN_CONTENT_WORDS = 3

# Palavras que não carregam conteúdo. Não é uma lista de parada completa nem
# precisa ser: serve só para contar o que sobra numa frase.
_FUNCTION_WORDS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "por", "pelo", "pela", "para", "pra", "pro",
    "com", "sem", "sob", "sobre", "ate", "e", "ou", "mas", "que", "se", "como",
    "quando", "porque", "entao", "assim", "ja", "so", "muito", "mais", "menos",
    "eu", "voce", "ele", "ela", "eles", "elas", "meu", "minha", "seu", "sua",
    "isso", "isto", "aquilo", "esse", "essa", "este", "esta", "aqui", "ali", "la",
    "ser", "estar", "ter", "vou", "vai", "vamos", "tem", "tá", "ta", "foi",
    "nao", "sim", "num", "numa", "todo", "toda", "todos", "todas", "outro", "outra",
}

# Aberturas que denunciam pedaço de conversa, não começo de afirmação.
_WEAK_OPENERS = {"ah", "eh", "oh", "opa", "po", "ne", "ta", "ué", "ue", "hein", "olha"}

# Inícios que podem ser verdadeiros dentro do discurso, mas dependem da frase
# anterior quando são promovidos sozinhos a headline. Não são remoções do
# transcript: apenas impedem que uma unidade de pausa seja apresentada como uma
# citação autossuficiente.
_CONTEXT_FRAGMENT_RE = re.compile(
    r"^(?:portanto|ou seja|ao mesmo tempo|para permitir|e\s+(?:a|o|as|os|um|uma)|"
    r"porque\s+(?:o|a|os|as|ele|ela|isso|esse|essa))\b",
    re.IGNORECASE,
)

# Erros recorrentes de concordância em ASR português. A citação não pode ser
# silenciosamente corrigida; ela precisa ser descartada ou marcada para áudio.
_POSSIBLE_ASR_AGREEMENT_RE = re.compile(
    # Não generalizar para qualquer palavra terminada em s/a/o: "está nos
    # assistindo" é perfeitamente válido. O vocabulário abaixo cobre formas
    # adjetivais/participiais que aparecem com frequência no ASR e cuja flexão
    # pode ser conferida sem inventar uma correção.
    r"\b(?:e|foi|esta|era|sera)\s+(?:tomados|tomadas|feitos|feitas|"
    r"dominados|dominadas|ocupados|ocupadas|fechados|fechadas)\b|"
    r"\b(?:sao|foram|estao|eram)\s+(?:tomado|tomada|feito|feita|"
    r"dominado|dominada|ocupado|ocupada|fechado|fechada)\b",
    re.IGNORECASE,
)

def headline_fragment_reason(text: str) -> str:
    """Return a stable reason when a quote is unsafe as a standalone headline."""
    folded = normalize(str(text or "").strip())
    if not folded:
        return "texto vazio"
    if _CONTEXT_FRAGMENT_RE.search(folded):
        return "começa como continuação da frase anterior"
    if _POSSIBLE_ASR_AGREEMENT_RE.search(folded):
        return "possível erro de concordância da transcrição; conferir no áudio"
    return ""

# Cortesia e protocolo. Não é headline, é o programa começando ou acabando.
_PLEASANTRY = (
    "bem-vindo", "bem vindo", "boa noite", "bom dia", "boa tarde", "obrigado",
    "obrigada", "prazer", "muito prazer", "parabens", "estamos junto", "valeu",
    "ate logo", "com a gente", "nosso tempo",
)

# Um "?" só conta como pergunta quando há uma palavra interrogativa. Numa legenda
# automática o ponto de interrogação cai em qualquer lugar: "Porque é estratégico
# e nós estamos num?" não é pergunta, é uma frase cortada no meio.
_INTERROGATIVE = {
    "que", "qual", "quais", "quem", "quando", "onde", "como", "porque", "por",
    "quanto", "quanta", "quantos", "quantas", "sera",
}

# O Renan encena a fala dos outros o tempo todo — o eleitor, o repórter, o
# bandido. Citar a encenação como se fosse a posição dele é a citação falsa mais
# fácil de cometer, e o rastro dela é o verbo de fala na frase anterior.
_SPEECH_CUE = re.compile(
    r"\b(?:fal(?:o|ei|ou|ando)|diss(?:e|eram)|dizer|dizendo|pergunt(?:a|ei|ou|aram)|"
    r"respond(?:e|i|eu)|grit(?:a|ei|ou)|chega\s+e\s+fala)\b"
)

# O verbo de fala nem sempre está na frase anterior. Quando o entrevistado entra
# na voz do personagem, o que denuncia é o vocativo de conversa de rua: "ô quantos
# votos vou trazer aqui, pô". Sem esta recusa, uma fala que ele estava *imitando*
# saiu como citação atribuída a ele — o erro mais caro que este módulo pode
# cometer, e ele apareceu numa legenda real do editor.
_ROLEPLAY_MARKER = re.compile(r"(?:^|\s)(?:ô|pô|ó|opa|ué|hein|oxe)(?:\s|[,.!?]|$)", re.IGNORECASE)

# Onde uma citação pode ser cortada sem virar outra frase. São fronteiras de
# oração: cortar antes delas deixa a oração principal inteira.
_CLAUSE_BREAKS = (
    ",", ";", ":", " — ", " – ",
    " e ", " mas ", " porque ", " porém ", " então ", " que ", " se ",
    " quando ", " enquanto ", " embora ", " ou ",
)

# Uma citação que termina numa destas fica pendurada e pode inverter o sentido:
# "Eu não sou contra…" não diz a mesma coisa que a frase inteira.
_DANGLING_TAIL = {
    "nao", "nunca", "jamais", "sem", "nem", "so", "ate", "muito", "mais", "menos",
    "e", "ou", "mas", "que", "se", "de", "do", "da", "em", "no", "na", "com",
    "por", "para", "pra", "pro", "um", "uma", "o", "a", "os", "as",
    # Legenda automática corta a frase no meio e põe pontuação ali. Terminar
    # numa destas é o rastro: "…a pessoa que tá?", "…nós estamos num?"
    "ta", "num", "numa", "tao", "vai", "vou", "foi", "esta", "estao", "eh",
}

# Ruído de reconhecimento e hesitação. Não se limpa a citação — escolhe-se outra.
_STUTTER = re.compile(r"\b(\w+)(\s+\1){1,}\b", re.IGNORECASE)
_HESITATION = {"eh", "ah", "hã", "ha", "ne", "tipo", "assim", "digamos", "enfim", "sabe"}

# Primeira pessoa: 11% das legendas do quartil mais visto contra 7% do menos
# visto, medido no Campaign Hub sobre 983 publicações de 2026.
_FIRST_PERSON = {
    "eu", "vou", "fui", "nosso", "nossa", "nossos", "nossas", "vamos", "nos",
    "pretendo", "quero", "acho", "defendo", "faco", "farei", "meu", "minha",
}

# Compromisso em primeira pessoa — o que autoriza o verbo "PROMETE".
# "vamos dizer" e "vamos falar" são muletas de conversa, não compromissos: elas
# davam a "E eles não estão em grande posição de, vamos dizer, de brigar" a marca
# de promessa em primeira pessoa, e com ela o verbo PROMETE na atribuição.
_COMMITMENT = re.compile(
    r"\b(?:eu\s+)?(?:vou|vamos|pretendo|pretendemos|farei|faremos|garanto|garantimos)\b"
    r"(?!\s+(?:dizer|falar|supor|imaginar|chamar))"
)

# Recusa explícita — o que autoriza "CRAVA".
_REFUSAL = re.compile(r"\b(?:jamais|nunca|de\s+jeito\s+nenhum|nao\s+vou|nao\s+vamos)\b")

# Vocabulário de confronto dirigido. Só ele autoriza o verbo mais forte.
_ATTACK = {
    "vagabundo", "vagabundos", "bandido", "bandidos", "ladrao", "ladroes",
    "corrupto", "corruptos", "roubalheira", "mentira", "mentiroso", "farsa",
    "vergonha", "absurdo", "podre", "inutilidade", "humilhante", "covarde",
    "malandro", "malandros", "hipocrisia", "descarado",
    # Calibrado contra a arte que o editor publicou: para a fala "o STF está uma
    # porcaria" ele escolheu BOMBA! e DETONA, e eu tinha lido apenas "alerta".
    # Desqualificação direta é confronto, e é o que decide o gancho e o verbo.
    "porcaria", "lixo", "palhacada", "vergonhoso", "escandalo", "escandalos",
    "desastre", "fracasso", "nojento", "asqueroso", "podridao", "picaretagem",
}

# Estampas, da mais forte para a mais branda. Nenhuma é obrigatória: um trecho
# sem carga sai sem estampa em vez de sair com uma inventada.
_STAMPS_ATTACK = ("VERGONHA!", "ABSURDO!", "OLHA ISSO")
_STAMPS_STAKES = ("ATENÇÃO", "GRAVE", "OLHA ISSO")
_STAMPS_CLAIM = ("ELE DISSE", "OLHA ISSO")


@dataclass(frozen=True)
class Quote:
    """Uma frase da transcrição, do jeito que ela foi dita."""

    text: str
    verbatim: bool
    start_s: float | None = None
    end_s: float | None = None
    score: float = 0.0
    reasons: tuple[str, ...] = field(default=())
    # "pontuacao" quando a fonte fecha frases, "pausa" quando a fronteira veio do
    # silêncio. O editor precisa da diferença: uma fronteira de pausa é real mas
    # não é fim de frase, e a citação tem de ser conferida no áudio antes das
    # aspas irem para a arte.
    boundary_source: str = "pontuacao"

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "verbatim": self.verbatim,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "character_count": len(self.text),
            "word_count": len(self.text.split()),
            "reasons": list(self.reasons),
            "boundary_source": self.boundary_source,
        }


@dataclass(frozen=True)
class Speaker:
    """Quem falou, e quem respondeu por isso.

    ``level`` é o que separa uma atribuição verificada de um chute:

    - ``audio`` — o reconhecimento de voz bateu com a amostra cadastrada;
    - ``editor`` — o editor escreveu quem é no contexto da fonte;
    - ``unknown`` — ninguém respondeu, e então a headline sai sem nome.
    """

    name: str = ""
    level: str = "unknown"

    @property
    def confirmed(self) -> bool:
        return self.level in {"audio", "editor"} and bool(self.name.strip())


# Uma pausa a partir daqui é fronteira de fôlego, e numa legenda sem pontuação é
# a única fronteira que existe. Não é fronteira de frase e não se finge que é.
PAUSE_BOUNDARY_S = 0.3
# Teto de uma unidade tirada de pausas. Sem pontuação nada fecha sozinho, e um
# bloco de cem palavras não é citação de coisa nenhuma.
UNIT_MAX_WORDS = 24


# Marcas de fim de frase por cem palavras. Medido em três fontes reais do editor:
# a legenda sobre compra de votos tem 0,16, o corte que ele montou à mão tem 0,61,
# e a entrevista do Metrópoles tem 6,10. O limiar fica no meio do vão, longe dos
# dois lados.
PUNCTUATION_PER_100_WORDS = 2.0


def transcript_is_punctuated(items: list[dict[str, Any]] | None) -> bool:
    """A fonte pontua? Metade das ferramentas de legenda não pontua nada.

    Sem essa pergunta o gerador exigia ponto final de uma legenda que não tem
    nenhum: numa fonte real de 111 linhas ele recusou tudo e devolveu a tela em
    branco.

    A pergunta é sobre a *densidade* de pontuação na fonte inteira, não sobre
    cada linha terminar em ponto. Uma legenda do YouTube quebra a linha onde ela
    encheu, então o ponto cai no meio dela constantemente — e perguntar linha a
    linha classificava uma fonte bem pontuada como sem pontuação, jogando fora as
    fronteiras de frase que ela de fato tinha.
    """
    texto = " ".join(str(item.get("text") or "") for item in items or [])
    palavras = len(texto.split())
    if palavras < 40:
        return True
    marcas = len(re.findall(r"[.!?]", texto))
    return (marcas / palavras) * 100 >= PUNCTUATION_PER_100_WORDS


def units_from_pauses(segments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Unidades de fala tiradas do silêncio, para legendas sem pontuação.

    Onde não há ponto final, a fronteira que existe é a pausa — e ela é real, o
    orador respirou ali. O que ela não é: uma fronteira de frase. Por isso cada
    unidade sai marcada com ``boundary_source``, e quem citar uma delas tem de
    dizer ao editor que o limite veio do silêncio e precisa ser conferido no
    áudio antes de virar aspas.
    """
    ordenados = sorted(
        (s for s in segments or [] if str(s.get("text") or "").strip()),
        key=lambda s: float(s.get("start", 0) or 0),
    )
    unidades: list[dict[str, Any]] = []
    atual: list[dict[str, Any]] = []

    def fechar(fonte="pausa"):
        if not atual:
            return
        texto = " ".join(str(s.get("text") or "").strip() for s in atual).strip()
        texto = " ".join(texto.split())
        if texto:
            unidades.append({
                "text": texto,
                "start": float(atual[0].get("start", 0) or 0),
                "end": float(atual[-1].get("end", 0) or 0),
                "boundary_source": fonte,
                # As linhas de onde a unidade foi feita. A arte que o editor
                # aprovou citou "O STF ESTÁ UMA PORCARIA" — a primeira linha de
                # uma unidade de vinte e três palavras. Sem guardar as peças, a
                # única forma de chegar nela seria recortar pelo meio, que é
                # justamente o que não se faz.
                "pieces": [
                    {
                        "text": " ".join(str(s.get("text") or "").split()),
                        "start": float(s.get("start", 0) or 0),
                        "end": float(s.get("end", 0) or 0),
                    }
                    for s in atual if str(s.get("text") or "").strip()
                ],
            })
        atual.clear()

    for posicao, segmento in enumerate(ordenados):
        # Metade dos arquivos de legenda tem cue contígua: a linha seguinte
        # começa um décimo de segundo depois da anterior, e nenhuma pausa passa
        # de 0,3 s. Fechando só *depois* de cruzar o teto, a legenda inteira
        # virava uma unidade de 29 palavras — acima do máximo — e a tela devolvia
        # zero headlines. Foi assim que o editor viu "não aparece nada".
        #
        # A quebra de linha é fronteira real, só de outra natureza: a pausa é
        # evidência de que o orador respirou, a linha é evidência de que quem
        # legendou achou que ela tinha enchido. Por isso ela fecha a unidade, e
        # por isso sai marcada com outro nome — uma citação tirada dali precisa
        # de conferência maior no áudio.
        adicionadas = len(str(segmento.get("text") or "").split())
        acumuladas = sum(len(str(s.get("text") or "").split()) for s in atual)
        if atual and acumuladas >= HEADLINE_MIN_WORDS and acumuladas + adicionadas > UNIT_MAX_WORDS:
            fechar("linha de legenda")

        atual.append(segmento)
        palavras = sum(len(str(s.get("text") or "").split()) for s in atual)
        proximo = ordenados[posicao + 1] if posicao + 1 < len(ordenados) else None
        pausa = (
            float(proximo.get("start", 0) or 0) - float(segmento.get("end", 0) or 0)
            if proximo else float("inf")
        )
        if pausa >= PAUSE_BOUNDARY_S and palavras >= HEADLINE_MIN_WORDS:
            fechar("pausa")
        elif palavras >= UNIT_MAX_WORDS:
            fechar("linha de legenda")
    fechar("pausa" if not unidades else "linha de legenda")

    # Uma pausa curta não deve transformar uma oração dependente em headline
    # isolada. Quando a próxima unidade é a continuação imediata e ainda cabe no
    # limite de unidade, reconstituímos a frase para preservar a tese completa.
    # Se não couber, o filtro continua recusando o fragmento, sem truncá-lo.
    reparadas: list[dict[str, Any]] = []
    for unidade in unidades:
        if reparadas:
            anterior = reparadas[-1]
            anterior_texto = str(anterior.get("text") or "")
            intervalo = float(unidade.get("start", 0) or 0) - float(anterior.get("end", 0) or 0)
            combinado = f"{anterior_texto} {str(unidade.get('text') or '').strip()}".strip()
            if (
                headline_fragment_reason(anterior_texto)
                and intervalo <= 1.2
                and len(combinado.split()) <= UNIT_MAX_WORDS
            ):
                anterior["text"] = combinado
                anterior["end"] = unidade.get("end", anterior.get("end"))
                anterior["boundary_source"] = "repaired_pause"
                anterior["pieces"] = [*(anterior.get("pieces") or []), *(unidade.get("pieces") or [])]
                continue
        reparadas.append(unidade)
    return reparadas


def sentences_from_segments(segments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """As frases do corte, com o tempo de cada uma.

    Onde a fonte pontua, usa o mesmo construtor do seletor de cortes de
    propósito. Uma linha de legenda não é uma frase — o ponto final cai no meio
    dela — e uma headline montada sobre a fronteira errada citaria o rabo de uma
    frase colado no começo da seguinte, que é literalmente uma citação falsa.

    Onde a fonte não pontua, não há fronteira de frase para encontrar e fingir
    que há seria pior que admitir. Aí a fronteira vem da pausa, e vem marcada.
    """
    if not segments:
        return []
    from .clip_selector import ClipSelector

    # A função de densidade trata fontes curtas como "não julgadas" para não
    # declarar qualidade a partir de poucas palavras. Para construir unidades,
    # porém, vários segmentos sem qualquer pontuação ainda não oferecem uma
    # fronteira de frase: usar o construtor de frases nesse caso cria uma única
    # unidade sem marca de pausa e depois o pick_quotes exige um ponto que a fonte
    # nunca poderia ter.
    raw_text = " ".join(str(item.get("text") or "") for item in segments)
    has_explicit_punctuation = bool(re.search(r"[.!?]", raw_text))
    if not has_explicit_punctuation or not transcript_is_punctuated(segments):
        return units_from_pauses(segments)
    return ClipSelector()._build_sentences(segments)


def sentences_from_text(text: str) -> list[dict[str, Any]]:
    """Frases de um texto sem tempo — uma edição já pronta, colada pelo editor."""
    pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if p.strip()]
    return [{"text": p, "start": None, "end": None} for p in pieces]


def _noise_penalty(text: str) -> float:
    """Quanto de ruído de reconhecimento a frase carrega."""
    folded = normalize(text)
    tokens = re.findall(r"[a-z0-9çãáéíóúâêôõà-]+", folded)
    if not tokens:
        return 100.0
    hesitations = sum(1 for token in tokens if token in _HESITATION)
    stutters = len(_STUTTER.findall(folded))
    return (hesitations / len(tokens)) * 60.0 + stutters * 25.0


def _content_words(folded: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", folded)
        if len(token) >= 4 and token not in _FUNCTION_WORDS
    ]


def _disqualify(text: str, cased: bool, punctuated: bool = True) -> str:
    """Por que esta frase não pode virar citação. Vazio quando pode.

    São recusas, não descontos. Uma frase que abre no meio de outra, que não
    afirma nada ou que é protocolo do programa não melhora por pontuar bem em
    outra coisa — e cada uma destas foi escolhida pela primeira versão deste
    gerador nos oito cortes reais da entrevista do Metrópoles.
    """
    stripped = text.strip()
    words = stripped.split()
    if len(words) < HEADLINE_MIN_WORDS:
        return "curta demais para afirmar alguma coisa"

    folded = normalize(stripped)
    if len(_content_words(folded)) < HEADLINE_MIN_CONTENT_WORDS:
        return "sem palavras de conteúdo suficientes"

    if any(term in folded for term in _PLEASANTRY):
        return "cortesia ou protocolo do programa"

    fragment_reason = headline_fragment_reason(stripped)
    if fragment_reason:
        return fragment_reason

    if _ROLEPLAY_MARKER.search(stripped):
        return "fala encenada na voz de outra pessoa"
    # "votos votos", "a a gente": repetição de reconhecimento. Numa arte isso lê
    # como defeito, e limpar seria reescrever — então escolhe-se outra frase.
    if _STUTTER.search(folded):
        return "repetição de palavra na transcrição"

    tokens = re.findall(r"[a-z0-9]+", folded)
    if not tokens:
        return "sem texto aproveitável"
    if tokens[0] in _WEAK_OPENERS:
        return "abre numa muleta de conversa"

    # A mesma pergunta que o corte faz da sua própria borda: esta frase começa
    # alguma coisa, ou continua a anterior? A resposta vem do mesmo lugar, de
    # propósito — uma citação que abre em "E eles não estão…" ou "Aí a emenda…"
    # tem o mesmo defeito de um corte que abre ali.
    from .clip_selector import ClipSelector

    if not ClipSelector._opens_a_thought(stripped, cased):
        return "continua a frase anterior em vez de começar uma"

    # Numa fonte que pontua, a falta de ponto final denuncia frase cortada. Numa
    # que não pontua, exigir ponto final recusa a fonte inteira — foi o que
    # devolveu tela em branco numa legenda real de 111 linhas.
    if punctuated:
        if not stripped.endswith((".", "!", "?")):
            return "sem fechamento de frase"
        if stripped.endswith("?") and not (set(tokens) & _INTERROGATIVE):
            return "ponto de interrogação sem pergunta"
    # Terminar em palavra funcional é fragmento com pontuação ou sem ela.
    if tokens[-1] in _DANGLING_TAIL:
        return "termina no meio de uma oração"

    return ""


def _score(text: str, cased: bool = False, punctuated: bool = True) -> tuple[float, list[str]]:
    """O quanto esta frase se sustenta sozinha numa arte."""
    stripped = text.strip()
    impedimento = _disqualify(stripped, cased, punctuated)
    if impedimento:
        return -1.0, [impedimento]

    folded = normalize(stripped)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    reasons: list[str] = []
    score = 50.0

    noise = _noise_penalty(stripped)
    score -= noise
    if noise > 12:
        reasons.append("ruído de reconhecimento na frase")

    if tokens & _FIRST_PERSON:
        score += 10.0
        reasons.append("primeira pessoa")
    if _COMMITMENT.search(folded):
        score += 10.0
        reasons.append("compromisso em primeira pessoa")
    if _REFUSAL.search(folded):
        score += 12.0
        reasons.append("recusa explícita")
    if tokens & _ATTACK:
        score += 16.0
        reasons.append("confronto dito com todas as letras")
    if stripped.endswith("?"):
        # 24% das legendas do quartil mais visto terminam em interrogação,
        # contra 18% do menos visto.
        score += 6.0
        reasons.append("termina em pergunta")

    # Densidade: uma frase de vinte palavras com quatro de conteúdo é enrolação.
    densidade = len(_content_words(folded)) / max(1, len(stripped.split()))
    score += min(14.0, densidade * 30.0)

    # Curto vence: da faixa mais curta para a mais longa a mediana de views cai
    # 36%. Aqui isso é ordenação, nunca recusa.
    excess = max(0, len(stripped) - QUOTE_IDEAL_CHARS)
    score -= excess * 0.35

    return score, reasons


def _trim_to_clause(text: str, limit: int) -> str:
    """Encurtar pelo fim numa fronteira de oração, ou devolver vazio.

    Devolver vazio é uma resposta legítima e é a diferença entre este passe e um
    truncamento: quando não há onde cortar sem mudar o que foi dito, a frase é
    descartada e outra é escolhida.
    """
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped

    janela = stripped[: limit + 1]
    corte = -1
    for marca in _CLAUSE_BREAKS:
        posicao = janela.rfind(marca)
        if posicao > corte:
            corte = posicao
    if corte <= 0:
        return ""

    parcial = stripped[:corte].strip(" ,;:—–-")
    palavras = parcial.split()
    if len(palavras) < QUOTE_MIN_WORDS:
        return ""
    ultima = normalize(palavras[-1])
    if ultima in _DANGLING_TAIL:
        return ""
    return f"{parcial}…"


def pick_quotes(
    sentences: list[dict[str, Any]],
    wanted: int = 3,
    is_other_speaker=None,
) -> list[Quote]:
    """As melhores frases do trecho para virarem citação, em ordem.

    ``is_other_speaker`` recebe o texto de uma frase e devolve verdadeiro quando
    ela é de outra pessoa — o entrevistador, tipicamente. Citar a pergunta como
    se fosse a resposta é o erro mais caro que esta função poderia cometer.
    """
    from .clip_selector import ClipSelector

    ordenadas = list(sentences or [])
    cased = ClipSelector._casing_is_meaningful(ordenadas)
    # ``sentences_from_segments`` pode já ter convertido uma fonte sem
    # pontuação em unidades delimitadas por pausa. Recalcular apenas pela
    # densidade da lista convertida faz uma legenda curta parecer pontuada
    # (por ter menos de 40 palavras) e recusa cada unidade por falta de ponto.
    # A marca de fronteira é a evidência mais específica disponível.
    has_pause_boundaries = any(
        str(item.get("boundary_source") or "") == "pausa" for item in ordenadas
    )
    punctuated = transcript_is_punctuated(ordenadas) and not has_pause_boundaries

    marcados: list[Quote] = []
    for posicao, frase in enumerate(ordenadas):
        bruto = str(frase.get("text") or "").strip()
        if not bruto:
            continue
        if is_other_speaker and is_other_speaker(bruto):
            continue
        # A frase anterior anuncia uma fala de terceiro? Então esta pode ser a
        # encenação, e não a posição de quem está sendo citado.
        if posicao and _SPEECH_CUE.search(normalize(str(ordenadas[posicao - 1].get("text") or ""))):
            continue

        pontos, motivos = _score(bruto, cased, punctuated)
        if pontos < 0:
            continue

        if len(bruto) <= QUOTE_MAX_CHARS:
            texto, literal = bruto, True
        else:
            texto = _trim_to_clause(bruto, QUOTE_MAX_CHARS)
            literal = False
            if not texto:
                continue
            motivos = [*motivos, "cortada numa fronteira de oração"]
            pontos -= 6.0

        marcados.append(Quote(
            text=texto,
            verbatim=literal,
            start_s=frase.get("start"),
            end_s=frase.get("end"),
            score=round(pontos, 2),
            reasons=tuple(motivos),
            boundary_source=str(frase.get("boundary_source") or "pontuacao"),
        ))

    marcados.sort(key=lambda item: (-item.score, len(item.text)))

    # Duas citações que dizem a mesma coisa não são duas opções.
    escolhidas: list[Quote] = []
    vistas: list[set[str]] = []
    for candidata in marcados:
        assinatura = {t for t in re.findall(r"[a-z0-9]+", normalize(candidata.text)) if len(t) >= 5}
        if any(assinatura and len(assinatura & anterior) / len(assinatura) > 0.6 for anterior in vistas):
            continue
        escolhidas.append(candidata)
        vistas.append(assinatura)
        if len(escolhidas) >= max(1, wanted):
            break
    return escolhidas


def attribution_verb(quote_text: str, signals: dict[str, Any] | None = None) -> str:
    """O verbo da atribuição, tirado do que a frase diz — não do que se supõe.

    O padrão é "DIZ", que é verdadeiro para qualquer frase. Os verbos mais fortes
    exigem evidência no próprio texto: um verbo forte é uma afirmação sobre como
    a pessoa falou, e errá-lo é atribuir a ela um tom que ela não teve.
    """
    folded = normalize(quote_text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    forca = float((signals or {}).get("conflict_or_stakes", 0) or 0)
    if tokens & _ATTACK and forca >= 45:
        return "DETONA"
    if _REFUSAL.search(folded):
        return "CRAVA"
    if _COMMITMENT.search(folded):
        return "PROMETE"
    return "DIZ"


def build_attribution(speaker: Speaker, quote_text: str, signals: dict[str, Any] | None = None) -> str:
    """`RENAN SANTOS DETONA:` — ou nada, quando ninguém respondeu por quem falou."""
    if not speaker.confirmed:
        return ""
    nome = re.sub(r"\s+", " ", speaker.name).strip().upper()
    if speaker.level == "audio":
        return f"{nome} {attribution_verb(quote_text, signals)}:"
    # O editor disse quem é, e isso responde "quem" — não responde "com que
    # força", que é uma leitura do áudio. Sem o áudio a atribuição sai sem verbo.
    return f"{nome}:"


def build_stamp(quote_text: str, signals: dict[str, Any] | None = None) -> str:
    """A estampa, tirada do tom da frase citada — vazia quando ela não o pede.

    O tom do corte inteiro não serve sozinho. Um corte carregado põe conflito
    alto no medidor, e a frase escolhida dele pode ser mansa: foi assim que
    "Vou pagar o preço se for o caso." saiu estampada de "VERGONHA!". A carga
    tem de estar na frase que o leitor vai ler; o sinal do corte só decide entre
    os graus que a frase já autoriza.
    """
    folded = normalize(quote_text)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    signals = signals or {}
    conflito = float(signals.get("conflict_or_stakes", 0) or 0)

    if tokens & _ATTACK:
        return _STAMPS_ATTACK[0] if conflito >= 45 else _STAMPS_ATTACK[1]
    if _REFUSAL.search(folded) or _COMMITMENT.search(folded):
        return _STAMPS_STAKES[0] if conflito >= 45 else _STAMPS_CLAIM[0]
    return ""


def stamp_alternatives(quote_text: str, signals: dict[str, Any] | None = None) -> list[str]:
    """As estampas possíveis para este tom, para o editor trocar sem reescrever."""
    principal = build_stamp(quote_text, signals)
    if not principal:
        return []
    for familia in (_STAMPS_ATTACK, _STAMPS_STAKES, _STAMPS_CLAIM):
        if principal in familia:
            return list(familia)
    return [principal]


def compose(quote: Quote, speaker: Speaker, signals: dict[str, Any] | None = None) -> dict[str, Any]:
    """A headline montada: estampa, atribuição e citação entre aspas."""
    atribuicao = build_attribution(speaker, quote.text, signals)
    citacao = f"“{quote.text}”"
    headline = f"{atribuicao} {citacao}".strip() if atribuicao else citacao
    return {
        "stamp": build_stamp(quote.text, signals),
        "stamp_alternatives": stamp_alternatives(quote.text, signals),
        "attribution": atribuicao,
        "attribution_level": speaker.level if speaker.confirmed else "nao_atribuida",
        "quote": quote.as_dict(),
        "headline": headline,
        "character_count": len(headline),
    }
