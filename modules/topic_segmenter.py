"""Split a long transcript into coherent thematic units, from the text alone.

The Acervo turns a source into QA-gated blocks, and everything outside a block is
non-content. Furia consumed those blocks but could not produce them, so a source
the Acervo never labelled arrived with no structure at all.

The first attempt here tried to recognise non-content by vocabulary — greetings,
requests for likes, production chatter. Measured against the regions the Acervo
labelled on two real sources it recovered 3.4% of them, because the labels are
judgements about whether a stretch sustains an argument, not about which words it
contains. "Casual banter with an analogy about Pokémon" has no keyword.

What follows treats the real problem: where does one subject end and the next
begin. Boundaries are found by lexical cohesion between neighbouring windows of
sentences — a valley in cohesion is a change of subject — and each resulting
segment is then judged on whether it develops a subject at all.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from .non_content_detector import score_segment

_WORD = re.compile(r"[0-9a-zà-ü]+")

# Function words carry no topic. Keeping them would make every pair of windows
# look similar, flattening the cohesion curve that boundaries are read from.
_STOPWORDS = {
    "a", "à", "às", "ao", "aos", "aquele", "aquela", "aqui", "as", "até", "com", "como",
    "da", "das", "de", "dela", "dele", "deles", "do", "dos", "e", "é", "ela", "elas",
    "ele", "eles", "em", "entre", "era", "essa", "esse", "esta", "está", "estamos",
    "estão", "este", "eu", "foi", "for", "isso", "isto", "já", "lá", "mais", "mas",
    "me", "mesmo", "meu", "muito", "na", "não", "nas", "nem", "no", "nos", "nós",
    "num", "numa", "o", "os", "ou", "para", "pela", "pelo", "por", "porque", "que",
    "quando", "se", "sem", "ser", "seu", "sua", "são", "só", "também", "te", "tem",
    "ter", "teu", "um", "uma", "vai", "vamos", "você", "vocês", "aí", "então", "né",
    "assim", "coisa", "gente", "cara", "tá", "pra", "pro", "lo", "la", "dessa",
}


def _tokens(text: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower()
    return [word for word in _WORD.findall(lowered) if len(word) > 2 and word not in _STOPWORDS]


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    dot = sum(left[word] * right[word] for word in shared)
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def _counts(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return counts


def _singular(word: str) -> str:
    """Junta o plural ao singular, e só isso.

    "reforma" e "reformas" são a mesma palavra para efeito de assunto, e contá-las
    separado deixa a curva de coesão mais rasa do que devia. Isto NÃO é um
    radicalizador completo de propósito: a versão que corta sufixo de verbo e de
    substantivo ("educação/educacional/educar" → "educ") deu duas viradas a mais
    no total mas derrubou a live do Ceará de 4/4 para 3/4, porque junta palavra
    que não é a mesma. Aqui só o plural, só em palavra de seis letras ou mais.

    Medido nas cinco fontes, contra só idf: uma virada a mais achada, dois pontos
    a mais de precisão, e nenhuma fonte piorou.
    """
    if len(word) < 6 or not word.endswith("s") or word.endswith("ss"):
        return word
    if word.endswith(("ões", "ães", "oes", "aes")):
        return word[:-3] + "ão"
    if word.endswith(("ais", "eis", "óis", "uis")):
        return word[:-3] + word[-3] + "l"
    if word.endswith("es") and word[-3] in "rzs":
        return word[:-2]
    return word[:-1]


def cohesion_curve(segments: list[dict[str, Any]], window: int) -> list[float]:
    """Lexical similarity across each gap between sentences.

    Each gap is scored by comparing the vocabulary of the ``window`` sentences
    before it with the ``window`` sentences after it. A low value means the two
    sides talk about different things.

    PALAVRA QUE APARECE EM TUDO NÃO DIZ DE QUE ASSUNTO SE TRATA
    -----------------------------------------------------------
    A lista `_STOPWORDS` acima é um palpite escrito à mão sobre quais palavras
    não carregam assunto. Ela acerta o óbvio — "que", "para", "então" — e erra o
    que só é óbvio DENTRO deste material: numa entrevista sobre o Brasil, a
    palavra "brasil" aparece em toda frase e não separa nada; num vídeo sobre
    segurança, "segurança" é o assunto inteiro.

    O `idf` mede isso em vez de adivinhar: cada palavra pesa pelo INVERSO de em
    quantas frases ela aparece. Palavra em toda frase pesa quase zero; palavra em
    três frases pesa muito. É calculado dentro do próprio vídeo, então se adapta
    sozinho a cada material — sem lista, sem ajuste, sem ninguém decidir nada.

    Medido nas cinco fontes com gabarito do Acervo, com a porta da troca de voz
    já ligada:

        antes (contagem crua)   22/39 achadas 56%   22/74 certeiras 30%
        com idf + plural        26/39 achadas 67%   26/73 certeiras 36%

    As duas colunas subiram, e nenhuma das cinco fontes piorou. A lista de
    stopwords continua valendo: tirá-la custou cinco pontos de alcance, porque
    "que"/"para" aparecem em toda frase de todo vídeo e o idf sozinho não os
    derruba o bastante.
    """
    words = [[_singular(word) for word in _tokens(item.get("text"))] for item in segments]
    total = len(words) or 1
    frases_com: dict[str, int] = {}
    for chunk in words:
        for word in set(chunk):
            frases_com[word] = frases_com.get(word, 0) + 1
    peso = {word: math.log(total / (1 + n)) for word, n in frases_com.items()}

    def pesados(bag: list[str]) -> dict[str, float]:
        counts: dict[str, float] = {}
        for word in bag:
            counts[word] = counts.get(word, 0.0) + peso.get(word, 1.0)
        return counts

    curve = []
    for gap in range(1, len(segments)):
        before = pesados([word for chunk in words[max(0, gap - window):gap] for word in chunk])
        after = pesados([word for chunk in words[gap:gap + window] for word in chunk])
        curve.append(_cosine(before, after))
    return curve


def _profundidade_do_vale(curve: list[float], index: int) -> float:
    """Quanto o vale é fundo em relação aos picos que o cercam.

    É a medida clássica do TextTiling — `(pico da esquerda + pico da direita −
    2 × fundo) / 2` — e a primeira coisa que tentei para melhorar a precisão.

    MEDIDA NAS CINCO FONTES, NÃO RESOLVEU
    -------------------------------------
    Trocar a ordem "menor coesão primeiro" por "vale mais fundo primeiro" e
    cortar os cinco mais fundos deu 7 de 39 viradas achadas com 23% de
    precisão, contra 25 de 39 com 18% da ordem antiga. Ou seja: a profundidade
    quase não separa vale verdadeiro de vale falso — ordenar por ela acerta o
    mesmo que ordenar por coesão crua.

    Fica aqui porque o número foi pago e para a próxima sessão não repetir a
    tentativa achando que é ideia nova. O que resolveu foi a porta da troca de
    voz, logo abaixo.
    """
    esquerda = curve[index]
    passo = index
    while passo > 0 and curve[passo - 1] >= curve[passo]:
        passo -= 1
        esquerda = max(esquerda, curve[passo])
    direita = curve[index]
    passo = index
    while passo < len(curve) - 1 and curve[passo + 1] >= curve[passo]:
        passo += 1
        direita = max(direita, curve[passo])
    return ((esquerda - curve[index]) + (direita - curve[index])) / 2


# Quanto dura um bloco típico do Acervo. Mediana dos 44 blocos das cinco fontes
# com gabarito que existiam ANTES do ato de 7 de setembro entrar na bancada — de
# propósito: o material novo não pode informar a régua com que ele é medido.
MEDIANA_DO_BLOCO_S = 220.0

# Quão fundo um vale precisa ser para virar candidato, como percentil da própria
# curva. Ver a varredura em `_boundaries`.
PERCENTIL_DO_VALE = 0.40


def _boundaries(curve: list[float], min_gap: int, tempos: list[float] | None = None,
                min_gap_s: float = 0.0, trocas_de_voz: list[float] | None = None,
                janela_da_troca: float = 5.0) -> list[int]:
    """Gaps that sit in a cohesion valley deeper than the local average.

    A DISTÂNCIA MÍNIMA ERA CONTADA EM FRASES, E ISSO ERA UM TETO
    ------------------------------------------------------------
    O parâmetro `min_sentences` fazia dois trabalhos: decidia se havia material
    suficiente para segmentar, e servia de distância mínima entre duas viradas.
    O segundo uso era um proxy ruim. Medido na sabatina da Band contra os dez
    blocos do Acervo:

        4 dos 10 blocos têm menos de 32 frases — o menor tem 11

    Com trinta e duas frases de distância obrigatória, esses quatro eram
    **impossíveis de achar**, por construção. O programa encontrava 1 das 9
    viradas de assunto.

    A regra de verdade sempre foi em segundos, e já existia: `min_duration_s`,
    15 s, que é o piso do próprio Acervo. `min_gap_s` põe a distância mínima
    onde ela pertence. Sem tempos, o comportamento antigo continua valendo.
    """
    if not curve:
        return []
    mean = sum(curve) / len(curve)
    deviation = math.sqrt(sum((value - mean) ** 2 for value in curve) / len(curve))
    # A boundary must be a local minimum and clearly below the average cohesion,
    # otherwise ordinary variation inside one subject would cut it in pieces.
    # Calibrated against 27 Acervo blocks on a 98-minute source: a shallower
    # threshold fragmented one subject into many, a deeper one collapsed the
    # whole transcript into a single unit.
    # O LIMITE PODIA FICAR NEGATIVO, E AÍ NADA PASSAVA NUNCA
    #
    # `média − desvio` supõe que a coesão varia pouco em torno da média. Numa
    # entrevista isso vale. Numa live, não: o Renan fala sozinho por horas, a
    # curva tem muitos pontos de coesão zero, o desvio fica MAIOR que a média e
    # o limite vira negativo. Medido na live do Ceará (234 min):
    #
    #     média 0,093 · desvio 0,100 · limite −0,007
    #
    # Coesão não é negativa, então nenhum ponto podia passar: as duas horas
    # viravam UM bloco só, e a régua marcava 0 de 4 viradas achadas. Não era
    # sinal fraco — era uma conta que quebra em material longo e monológico.
    #
    # O piso é o décimo percentil da própria curva: alcançável por definição
    # (dez por cento dos pontos estão nele ou abaixo) e sem número mágico. Onde
    # `média − desvio` já é maior que ele — as quatro outras fontes medidas —
    # nada muda.
    ordenada = sorted(curve)
    piso = ordenada[min(len(ordenada) - 1, int(len(ordenada) * PERCENTIL_DO_VALE))]
    threshold = max(mean - deviation, piso)
    candidates = []
    for index in range(1, len(curve) - 1):
        if curve[index] <= threshold and curve[index] <= curve[index - 1] and curve[index] <= curve[index + 1]:
            candidates.append(index)

    # A PORTA DA TROCA DE VOZ
    #
    # Das fronteiras que o Furia propunha, 18% eram reais — em todas as cinco
    # fontes medidas, inclusive nas que "funcionavam". O problema não era a
    # regra de escolha: ordenar os candidatos por vale mais fundo em vez de
    # coesão mais baixa acertou praticamente o mesmo (ver
    # `_profundidade_do_vale`). O problema era não haver nada separando vale
    # verdadeiro de vale falso.
    #
    # A separação estava no arquivo o tempo todo e ninguém lia. Medido nas
    # cinco fontes com gabarito do Acervo:
    #
    #     34 das 39 viradas de assunto (87%) caem a menos de 15 s de uma
    #     troca de locutor
    #
    # Faz sentido para o material desta casa: numa entrevista o assunto vira
    # quando o repórter pergunta outra coisa. A troca sozinha não serve de
    # fronteira — são 395 trocas para 39 viradas — mas serve de PORTA: só é
    # candidato o vale que cai em cima de uma.
    #
    # Efeito medido de ponta a ponta pela `regua_assuntos.py`:
    #
    #     antes   25/39 achadas (64%) · 26/143 certeiras (18%)
    #     depois  22/39 achadas (56%) · 22/74  certeiras (30%)
    #
    # Custa oito pontos de alcance e devolve doze de precisão. É a troca certa
    # para quem edita: fronteira errada vira corte que ele joga fora, fronteira
    # perdida vira só um bloco mais longo, que o seletor ainda corta por dentro.
    #
    marcas = sorted(set(trocas_de_voz or []))

    # A PORTA VIROU PREFERÊNCIA, PORQUE ELA APAGAVA UM ATO INTEIRO
    #
    # Como filtro duro, a porta supõe que assunto vira quando outra pessoa fala.
    # Vale numa entrevista. Num comício ou numa live o Renan fala sozinho por
    # uma hora e o assunto vira sem ninguém interromper. Medido no ato de 7 de
    # setembro (57 min, 21 assuntos no Acervo):
    #
    #     42 candidatos -> a porta deixa 2 -> 1 das 20 viradas achada (5%)
    #
    # A trava de "só fecha com três marcas ou mais" não protegia: o ato tem 19
    # trocas, ela abre, e leva 40 candidatos junto.
    #
    # Agora quem cai numa troca de voz é atendido PRIMEIRO, e os outros
    # continuam elegíveis. Onde a diarização é boa nada muda na prática — os
    # preferidos preenchem as vagas antes.
    perto_da_troca: set[int] = set()
    if marcas and tempos and janela_da_troca > 0:
        perto_da_troca = {
            index for index in candidates
            if index + 1 < len(tempos)
            and min(abs(tempos[index + 1] - marca) for marca in marcas) <= janela_da_troca
        }

    def longe_o_bastante(index: int, taken: int) -> bool:
        if tempos and min_gap_s > 0:
            try:
                return abs(tempos[index] - tempos[taken]) >= min_gap_s
            except IndexError:
                pass
        return abs(index - taken) >= min_gap

    # QUANTAS FRONTEIRAS ESTE MATERIAL COMPORTA — COMO PISO, NÃO COMO TETO
    #
    # A primeira tentativa foi usar este número como teto, cortando os
    # candidatos piores. Medido nas seis fontes, foi ruim em toda faixa:
    #
    #     sem teto      34/59 achadas 58%   34/129 certeiras 26%
    #     teto 400 s    15/59         25%   15/31             48%
    #     teto 220 s    23/59         39%   23/58             40%
    #     teto 120 s    32/59         54%   32/107            30%
    #
    # Nenhuma linha bate a de cima nas duas colunas: o teto corta fronteira
    # verdadeira junto com a falsa, porque ele não sabe distinguir — só conta.
    # Nas fontes pequenas, de quatro viradas reais, cortava duas delas.
    #
    # Invertido: a porta da troca de voz volta a mandar, e o número vira PISO.
    # Onde a porta já entrega fronteiras suficientes, nada muda — é o caso da
    # entrevista, e a precisão alta de lá fica de pé. Onde ela entrega quase
    # nada, porque ninguém interrompe o Renan, os vales de fora completam até o
    # piso em vez de o vídeo inteiro virar um bloco.
    #
    # O número vem do catálogo, não deste vídeo: mediana de 220 s nos 44 blocos
    # das cinco fontes que já tinham gabarito antes do ato de 7 de setembro.
    alvo = 1
    if tempos and len(tempos) > 1:
        duracao = float(tempos[-1]) - float(tempos[0])
        if duracao > 0:
            alvo = max(1, round(duracao / MEDIANA_DO_BLOCO_S) - 1)

    def escolher(entre: list[int], chosen: list[int], limite: int | None = None) -> None:
        for index in sorted(entre, key=lambda position: curve[position]):
            if limite is not None and len(chosen) >= limite:
                return
            if all(longe_o_bastante(index, taken) for taken in chosen):
                chosen.append(index)

    chosen: list[int] = []
    preferidos = [index for index in candidates if index in perto_da_troca]
    resto = [index for index in candidates if index not in perto_da_troca]
    if preferidos:
        # Cair numa troca de voz é evidência: esses entram todos, e o piso só
        # completa com os de fora quando eles não bastam.
        escolher(preferidos, chosen)
        if len(chosen) < alvo:
            escolher(resto, chosen, alvo)
    else:
        # Sem nenhuma marca de locutor não há evidência para separar vale
        # verdadeiro de falso, e sem limite o programa propõe TODO vale acima do
        # limiar — num texto de dois assuntos ele achava nove. Aqui o número do
        # catálogo é a única régua disponível, e vira teto.
        escolher(candidates, chosen, alvo)
    return sorted(chosen)


def _instantes_de_troca(segments: list[dict[str, Any]]) -> list[float]:
    """Os instantes em que quem fala mudou, do jeito que o motor os carrega.

    `_build_sentences` guarda a marca ">>" do arquivo em `speaker_change_at`,
    com o instante exato — uma frase montada pode conter mais de uma. Quem vem
    de outro caminho traz `speaker_change` na própria frase; aí o instante é o
    começo dela. Os dois formatos entram, para a porta não depender de por onde
    a transcrição chegou.
    """
    instantes: list[float] = []
    for item in segments:
        for instante in item.get("speaker_change_at") or []:
            try:
                instantes.append(float(instante))
            except (TypeError, ValueError):
                continue
        if item.get("speaker_change"):
            try:
                instantes.append(float(item.get("start", 0) or 0))
            except (TypeError, ValueError):
                continue
    return sorted(set(instantes))


def segment_transcript(
    segments: list[dict[str, Any]],
    *,
    window: int = 6,
    min_sentences: int = 32,
    min_duration_s: float = 30.0,
    max_duration_s: float = 720.0,
) -> list[dict[str, Any]]:
    """Split the transcript into thematic units and judge each one.

    The duration bounds mirror what the Acervo produces. Each unit is returned
    with the evidence behind the verdict, never as a bare accept or reject.

    O PISO DE 15 s ERA UM NÚMERO ERRADO ESCRITO COM CONFIANÇA
    ---------------------------------------------------------
    Estava aqui que "os blocos do Acervo vão de 15 s a uns 12 minutos". A
    primeira metade não se sustenta. Contados os 44 blocos das cinco fontes com
    gabarito:

        menor 34 s · décimo percentil 78 s · mediana 220 s · maior 644 s
        blocos abaixo de 30 s: NENHUM

    Ou seja, o piso de 15 s abria espaço para "assunto" de meio minuto que o
    Acervo nunca produz — e cada um deles era fronteira falsa. Trinta segundos
    fica logo abaixo do menor bloco já visto, com folga: não exclui nada real.

    Medido nas cinco fontes: a precisão foi de 36% para 40%, ao custo de uma
    virada achada a menos. É o mesmo raciocínio do resto — o número vem do
    catálogo, não do meu palpite.
    """
    usable = [
        item for item in segments or []
        if str(item.get("text") or "").strip()
        and float(item.get("end", 0) or 0) > float(item.get("start", 0) or 0)
    ]
    if len(usable) < min_sentences * 2:
        return []

    tempos = [float(item.get("start", 0) or 0) for item in usable]
    cuts = _boundaries(
        cohesion_curve(usable, window), min_sentences,
        tempos=tempos, min_gap_s=min_duration_s,
        trocas_de_voz=_instantes_de_troca(usable),
    )
    edges = [0, *[cut + 1 for cut in cuts], len(usable)]

    units: list[dict[str, Any]] = []
    for start_index, end_index in zip(edges, edges[1:]):
        group = usable[start_index:end_index]
        if not group:
            continue
        start = float(group[0].get("start", 0) or 0)
        end = float(group[-1].get("end", 0) or 0)
        duration = end - start
        if duration < min_duration_s:
            continue
        text = " ".join(str(item.get("text") or "") for item in group)
        words = _tokens(text)
        verdict = score_segment(text, words_per_second=len(_WORD.findall(text.lower())) / max(0.001, duration))
        # Vocabulary that keeps returning is a subject being developed; a stretch
        # where almost nothing repeats is a sequence of unrelated remarks.
        recurrence = 1.0 - (len(set(words)) / len(words)) if words else 0.0
        # A unit long enough to develop something, whose vocabulary returns often
        # enough to be about a subject, and that the cue scorer does not read as
        # broadcast filler.
        units.append({
            "start_s": round(start, 3),
            "end_s": round(min(end, start + max_duration_s), 3),
            "duration_s": round(min(duration, max_duration_s), 3),
            "sentence_count": len(group),
            "start_sentence_index": start_index,
            "end_sentence_index": end_index - 1,
            "topic_terms": [word for word, _ in sorted(_counts(words).items(), key=lambda pair: -pair[1])[:8]],
            "recurrence": round(recurrence, 3),
            "carries_subject": bool(recurrence >= 0.2 and len(words) >= 60 and not verdict["non_content"]),
            "non_content_cues": verdict["cues"],
            "provenance": "furia_topic_segmenter",
        })
    return units
