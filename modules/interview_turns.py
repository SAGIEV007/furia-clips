"""Find where the interviewer speaks, and treat that as the seam of the material.

An interview is not a stream of sentences: it is a sequence of question and
answer. Every boundary the Acervo drew on a 31-minute sabatina falls on the
moment the interviewer takes the floor again — measured, not assumed: all
fourteen blocks it published for that source open on an interviewer turn.

That matters because a cut that ignores those seams breaks in the two ways an
editor complains about. It ends after the next question has already begun, so
the clip carries a dangling question nobody answers; or it stops in the middle
of an answer, so the argument is delivered without its conclusion — and an
argument cut before its conclusion can read as the opposite of what was said.

The detector is deliberately narrow. It only reports a turn when the sentence
addresses the guest in the second person formal, or formulates a question in the
first person. On the measured source that yielded thirty turns and every one of
them was really the interviewer: no sentence of the guest's own speech was
mistaken for one. Recall is the side that gives: four of the fourteen block
openings use no form of address at all ("Mas qual é a punição?") and are missed.
That trade is the right way round — a missed seam leaves a cut longer than
ideal, while an invented seam would end a cut in the middle of a sentence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


# Second person formal, and the possessives that go with it. The guest answers
# in the first person and addresses the room as "você"; these forms belong to
# whoever is questioning him.
_ADDRESS = (
    # "candidato" is deliberately absent: on its own the word is as often the
    # anchor talking *about* the guest ("é o candidato do Missão, Renan Santos")
    # as it is somebody talking *to* him. Whole-word matching already stopped
    # "os seis candidatos" from counting; it cannot tell those two apart, and
    # counting the third-person mention put a turn at 31.6s of the sabatina —
    # inside the studio reading the running order. The alignment pass then
    # opened a clip there, undoing the guard that had just moved it past the
    # presentation. The vocative form is picked up by ``addresses_the_guest``.
    # "deputado" e "governador" saíram daqui pelo mesmo motivo que "candidato":
    # são tão usados na terceira pessoa quanto no vocativo. Medido na sabatina
    # da Band, "a emenda do deputado aliado" — o Renan explicando como um
    # prefeito ganha eleição — era lido como alguém CHAMANDO um deputado, e o
    # corte, que é bom, entrava marcado como fala do entrevistador. Enquanto a
    # marcação só ia para revisão isso passava despercebido; agora que ela
    # desconta nota, custaria caro num corte que presta.
    #
    # As duas continuam valendo na forma vocativa ("Deputado, o senhor acha?"),
    # que é onde elas realmente marcam quem fala, por ``addresses_the_guest``.
    " o senhor ", " ao senhor ", " do senhor ", " pro senhor ", " para o senhor ",
    " senhor ", " dos senhores ", " presidente eleito",
    " seu plano", " seu programa", " seu governo", " sua proposta", " suas propostas",
    " no seu livro", " as suas ", " os seus ", " sua candidatura",
)

# Explicit formulation of a question. "eu quero" and "eu queria" are left out on
# purpose: the guest uses them constantly ("eu quero que a família saiba") and
# they cost more in false turns than they buy in recall.
_ASKS = (
    " eu te pergunto", " te pergunto", " minha pergunta", " pergunto ao",
    " me diga", " me responde", " queria saber do senhor",
)

# A turn that changes the subject rather than pressing on the same one. These are
# the phrases an interviewer uses to close one theme and open the next.
_SHIFT = (
    " agora,", " outro ponto", " outra pergunta", " mudando de assunto", " sobre isso",
    " falando em", " falando sobre", " vamos falar", " vamos dar", " comeca falando",
    " seguindo nessa", " continuar nesse tema", " nosso tempo", " outro tema",
    " proximo tema", " boa noite", " ultima pergunta", " para terminar",
)

# Intervalos são uma fronteira de transmissão, não uma pergunta nem uma resposta.
# O detector exige vocabulário de chamada/retorno, em vez de marcar toda menção
# genérica à palavra "intervalo" como pausa editorial.
_BROADCAST_BREAK_START_RE = re.compile(
    r"\b(?:vamos|faremos|vamos fazer|vamos para|vamos ao|vamos a)\b"
    r"[^.!?]{0,70}\bintervalo\b"
    r"|\bintervalo\b[^.!?]{0,70}\b(?:voltamos|volta)\b"
    # "Renan, eu preciso chamar aqui o nosso intervalo": é assim que quem
    # apresenta anuncia a pausa, e o vocabulário acima não pegava — nem
    # "vamos", nem "voltamos". Na sabatina da Band esse corte tirou a quarta
    # melhor nota da rodada. O verbo é "chamar", e ele exige o intervalo
    # logo adiante para não confundir com "chamar para o debate".
    r"|\bchamar\b[^.!?]{0,40}\bintervalo\b"
    r"|\b(?:pausa|breve pausa)\b[^.!?]{0,30}\b(?:comercial|publicidade)\b"
)
_BROADCAST_RETURN_RE = re.compile(
    r"\b(?:estamos|a gente está|a gente esta)\s+de volta\b"
    r"|\b(?:a gente|nós|nos)\s+volt(?:a|amos)\b[^.!?]{0,32}"
    r"|\bvoltamos\b"
    r"|\b(?:após|apos|depois do|depois desse|depois deste)\s+intervalo\b"
)


def classify_broadcast_boundary(text: str) -> str | None:
    """Classify an explicit broadcast break/return, or return ``None``.

    The positive vocabulary is intentionally narrow. A sentence such as
    "o intervalo entre duas sessões" is not enough; a call to pause or a clear
    return announcement is required. When one sentence contains both sides of
    the handoff, ``break_start_and_return`` keeps it hard-boundary.
    """
    normalized = _normalize(text)
    is_start = bool(_BROADCAST_BREAK_START_RE.search(normalized))
    is_return = bool(_BROADCAST_RETURN_RE.search(normalized))
    if is_start and is_return:
        return "break_start_and_return"
    if is_start:
        return "break_start"
    if is_return:
        return "return"
    return None


def is_broadcast_break_sentence(text: str) -> bool:
    """Whether a transcript sentence explicitly announces a break or return."""
    return classify_broadcast_boundary(text) is not None


# ─── O programa se administrando ────────────────────────────────────────────
#
# Existe uma terceira coisa numa entrevista, que não é pergunta nem resposta: o
# programa cuidando de si mesmo. "A gente precisa finalizar um minuto", "na
# sequência, considerações finais", "deixa eu colocar um outro assunto aqui na
# roda". Quem fala é quem apresenta, e o assunto é o próprio programa.
#
# Nada disso vira corte. Medido na sabatina da Band, três dos doze melhores
# cortes entregues abriam exatamente assim — um deles com nota 79.
#
# O vocabulário é estreito de propósito, como o do intervalo. Cada expressão
# aqui é uma forma de administrar o tempo do programa, não de discutir um
# assunto: "nosso tempo" não é o mesmo que "o tempo do país".
_FALA_DE_MESA_RE = re.compile(
    r"\b(?:precisa|precisamos|preciso|temos que|tenho que)\b[^.!?]{0,24}\bfinalizar\b"
    r"|\bconsidera(?:c|ç)(?:oes|ões) finais\b"
    r"|\b(?:nosso|o nosso) tempo\b[^.!?]{0,24}\b(?:acabou|acabando|estourou|curto)\b"
    r"|\b(?:ultimo|último|proximo|próximo) bloco\b"
    r"|\bdeixa eu (?:colocar|trazer|puxar)\b[^.!?]{0,30}\b(?:assunto|tema|roda|pauta)\b"
    r"|\b(?:passo|passamos|devolvo) a palavra\b"
    r"|\b(?:vamos|vou) (?:para|ao|a) (?:o|a)? ?(?:nosso|nossa)? ?(?:proximo|próximo|ultimo|último)\b"
)

# Cortesia: cumprimento e agradecimento sem tese nenhuma dentro.
#
# "Bom, de fato é minha primeira vez aqui. Queria agradecer a Band, agradecer
# todo o time." — quem fala é o entrevistado, então nenhum detector de
# entrevistador pega, e mesmo assim não é corte: não afirma nada. Tirou nota 79
# na sabatina.
_CORTESIA_RE = re.compile(
    r"\b(?:queria|quero|gostaria de|vim) agradecer\b"
    r"|\bobrigado (?:pelo|pela|por)\b[^.!?]{0,24}\b(?:convite|espa(?:c|ç)o|oportunidade)\b"
    r"|\bagrade(?:c|ç)o (?:o|pelo|a|pela)\b[^.!?]{0,24}\b(?:convite|espa(?:c|ç)o|oportunidade)\b"
    r"|\b(?:minha|a minha) primeira vez aqui\b"
    r"|\b(?:boa noite|bom dia|boa tarde) (?:a todos|a todas|pra voc|para voc)\b"
)


def is_studio_housekeeping(text: str) -> bool:
    """Whether the sentence is the programme managing itself.

    Encerramento, anúncio de bloco, passagem de palavra, mudança de assunto
    conduzida pela mesa. Não é o intervalo (que tem detector próprio) nem uma
    pergunta: é a produção aparecendo na transcrição.
    """
    return bool(_FALA_DE_MESA_RE.search(_normalize(text)))


def is_courtesy_sentence(text: str) -> bool:
    """Whether the sentence is greeting or thanks with no claim inside."""
    return bool(_CORTESIA_RE.search(_normalize(text)))


def opens_without_a_claim(text: str) -> str | None:
    """Name the reason this opening carries no editorial content, or ``None``.

    Uma só porta para as três coisas que nunca são a abertura de um corte: o
    intervalo, o programa se administrando, e a cortesia.
    """
    if classify_broadcast_boundary(text) is not None:
        return "intervalo"
    if is_studio_housekeeping(text):
        return "fala_de_mesa"
    if is_courtesy_sentence(text):
        return "cortesia"
    return None

# Below this a turn is an interruption inside the answer, not a new question:
# "Senhor manter então para a extrema pobreza até fazer a transição." The guest
# resumes the same argument straight after, so a cut may run through it.
INTERJECTION_MAX_WORDS = 12

# A press-conference question is short. "Candidato, quais os compromissos que o
# seu governo teria com a Paraíba?" is eleven words, and counting words alone
# filed it as an interruption — so it never opened a block, and the clip that
# carried it had to drag in the tail of the previous answer to reach it. The
# editor saw both halves of that on the João Pessoa cuts: one clip running past
# "essa é uma questão muito importante", the next starting on exactly that
# overrun instead of on "candidato".
#
# The fragment the rule above exists to catch is not short — it is *incomplete*.
# Grammar separates the two where length cannot.
# "porque" numa palavra é a conjunção causal — "é porque naturalmente eles
# concordam" —, não a interrogativa, que em português se escreve separada. Ela
# estava na lista, e junto com a limpeza de vocativo abaixo ("isso, é porque"
# vira "é porque") transformava uma explicação em pergunta: na coletiva de João
# Pessoa isso pôs uma fronteira de bloco no meio de uma frase do próprio Renan.
_QUESTION_OPENERS = (
    "quais", "qual", "quantos", "quantas", "quanto", "como", "quando",
    "onde", "quem", "por que", "o que", "que tipo", "sera",
)
# A vocative may come first: "Candidato, quais...", "Renan, por que...".
_LEADING_VOCATIVE = re.compile(r"^[^,?!.]{1,28},\s*")


def is_a_whole_question(text: str) -> bool:
    """Whether the interviewer's own words form a whole question.

    The question mark is the reliable signal. Where the source carries no
    punctuation at all it is missing, and the fallback only recognises questions
    that *open* with an interrogative word — a yes/no question ("o senhor
    pretende manter o programa") is indistinguishable from a statement without
    punctuation, and guessing there would put a block boundary inside an answer.
    Those keep being judged by length, which is the honest limit of this rule.
    """
    stripped = str(text or "").strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    # The vocative may or may not carry its comma — an unpunctuated source has
    # neither the comma nor the question mark — so the opener is accepted in the
    # first position or the second, and nowhere else.
    tokens = _normalize(_LEADING_VOCATIVE.sub("", stripped)).split()
    for offset in (0, 1):
        head = " ".join(tokens[offset:offset + 2])
        if any(head == marker or head.startswith(f"{marker} ") for marker in _QUESTION_OPENERS):
            return True
    return False
# Consecutive flagged sentences this close together are one turn, not several —
# in the order of the transcript and in the clock, because on a coarsely
# segmented source the two come apart.
_TURN_GAP_SENTENCES = 3
_TURN_GAP_SECONDS = 25.0


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower().replace("ç", "c")
    return " " + " ".join(lowered.split()) + " "


def _phrases(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Match the terms as whole words.

    Substring matching read "os seis **candidato**s mais bem colocados" — the
    anchor listing who will be interviewed — as the vocative "candidato", and
    with it the whole opening of the broadcast became an interviewer turn.
    """
    return re.compile(r"(?:^|(?<=\W))(?:" + "|".join(re.escape(term.strip()) for term in terms) + r")(?=\W|$)")


_ADDRESS_RE = None
_ASKS_RE = None


def is_interviewer_sentence(text: str) -> bool:
    """True when this sentence is the interviewer speaking, not the guest."""
    global _ADDRESS_RE, _ASKS_RE
    if _ADDRESS_RE is None:
        _ADDRESS_RE = _phrases(_ADDRESS)
        _ASKS_RE = _phrases(_ASKS)
    normalized = _normalize(text)
    if _ADDRESS_RE.search(normalized) or _ASKS_RE.search(normalized):
        return True
    # "Candidato, boa noite." is the interviewer; "o candidato do Missão" is the
    # anchor. Only the vocative counts, and that distinction already lives in
    # ``addresses_the_guest``.
    return addresses_the_guest(text)


def detect_interviewer_turns(sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group the transcript into the moments the interviewer takes the floor.

    Each turn carries the time it opens at, how many words it runs for, and
    whether it reads as a change of subject. Callers use ``major`` to decide what
    a clip may cross and ``interjection`` to decide what it may end on.
    """
    ordered = [
        item for item in sentences or []
        if str(item.get("text") or "").strip()
        and float(item.get("end", 0) or 0) > float(item.get("start", 0) or 0)
    ]
    ordered.sort(key=lambda item: float(item.get("start", 0) or 0))
    if not ordered:
        return []

    def likely_question_continuation(index: int) -> bool:
        """Recognize an unlabelled question when a nearby line confirms the interviewer.

        Imported captions often split one interviewer question into several short
        lines. A line such as ``ao voto do cidadão?`` has no vocative by itself,
        while the next line may contain ``seu programa`` and clearly identify the
        same interviewer turn. Guest rhetorical questions are not promoted unless
        a nearby sentence supplies that independent interviewer evidence.
        """
        text = str(ordered[index].get("text") or "")
        if not is_a_whole_question(text):
            return False
        current_end = float(ordered[index].get("end", 0) or 0)
        for following in ordered[index + 1:index + 4]:
            following_start = float(following.get("start", 0) or 0)
            if following_start - current_end > _TURN_GAP_SECONDS:
                break
            following_text = str(following.get("text") or "")
            if classify_broadcast_boundary(following_text) is not None:
                break
            if is_interviewer_sentence(following_text):
                return True
            if len(following_text.split()) > 6 and not is_a_whole_question(following_text):
                break
        return False

    flagged = [
        index for index, item in enumerate(ordered)
        if is_interviewer_sentence(item["text"])
        or classify_broadcast_boundary(item["text"]) is not None
        or likely_question_continuation(index)
    ]
    if not flagged:
        return []

    groups: list[list[int]] = []
    for index in flagged:
        current_has_broadcast = bool(groups) and any(
            classify_broadcast_boundary(ordered[position]["text"]) is not None
            for position in groups[-1]
        )
        item_has_broadcast = classify_broadcast_boundary(ordered[index]["text"]) is not None
        # A break always starts a new turn instead of being merged into the
        # preceding question merely because the clock gap is short. Its own
        # return sentence may join the same hard-boundary turn.
        joins_broadcast = current_has_broadcast and item_has_broadcast
        near_in_order = bool(groups) and index - groups[-1][-1] <= _TURN_GAP_SENTENCES
        # Proximity in the transcript is not proximity in time. On a source
        # transcribed in long segments, two questions five minutes apart can sit
        # three sentences apart, and merging them produced a single "turn"
        # spanning the whole interview.
        near_in_time = bool(groups) and (
            float(ordered[index].get("start", 0) or 0)
            - float(ordered[groups[-1][-1]].get("end", 0) or 0)
        ) <= _TURN_GAP_SECONDS
        between = ordered[groups[-1][-1] + 1:index] if groups else []
        # A new flagged question after a substantive guest sentence is a new
        # interviewer turn. Very short fragments remain eligible as a split
        # question or acknowledgement, which is important for coarse captions.
        substantive_answer_between = any(
            classify_broadcast_boundary(str(item.get("text") or "")) is None
            and not is_interviewer_sentence(str(item.get("text") or ""))
            and len(str(item.get("text") or "").split()) > 6
            for item in between
        )
        if joins_broadcast or (
            near_in_order and near_in_time
            and not current_has_broadcast and not item_has_broadcast
            and not substantive_answer_between
        ):
            groups[-1].append(index)
        else:
            groups.append([index])

    turns: list[dict[str, Any]] = []
    for group in groups:
        first, last = group[0], group[-1]
        broadcast_items = [
            classify_broadcast_boundary(ordered[i]["text"]) for i in group
        ]
        has_broadcast = any(item is not None for item in broadcast_items)
        # A normal question may spill one sentence past its last flagged line,
        # where the question mark lands. A broadcast turn must not absorb the
        # first editorial question after the return.
        tail = last if has_broadcast else min(len(ordered) - 1, last + 1)
        spoken = " ".join(str(ordered[i].get("text") or "") for i in range(first, last + 1))
        text = " ".join(str(ordered[i].get("text") or "") for i in range(first, tail + 1))
        # A question can occupy several caption lines after the last line that
        # carries a lexical interviewer marker. Extend only an already flagged
        # interviewer group, and only until its next question mark; a normal
        # guest answer after a complete question is therefore left untouched.
        question_tail = last
        if not has_broadcast and any(is_interviewer_sentence(ordered[i]["text"]) for i in group):
            probe = last
            joined = spoken
            while "?" not in joined and probe < len(ordered) - 1 and probe - last < 3:
                probe += 1
                probe_text = str(ordered[probe].get("text") or "")
                if classify_broadcast_boundary(probe_text) is not None:
                    break
                joined = f"{joined} {probe_text}".strip()
                if "?" in joined:
                    question_tail = probe
                    break
        # Only the sentences actually recognised as the interviewer's count
        # towards the length: the sentence after them is usually the guest
        # already answering, and including it inflates every short aside into a
        # question of its own.
        words = len(spoken.split())
        shift = any(k in _normalize(text) for k in _SHIFT)
        # Measured on what the interviewer actually said, never on the tail
        # sentence — that one is usually the guest already answering, and its
        # punctuation would speak for a turn it does not belong to.
        question = (
            (is_a_whole_question(spoken) or is_a_whole_question(text))
            if not has_broadcast else False
        )
        break_start = any(
            item in {"break_start", "break_start_and_return"}
            for item in broadcast_items
        )
        returned = any(
            item in {"return", "break_start_and_return"}
            for item in broadcast_items
        )
        turns.append({
            "start_s": round(float(ordered[first].get("start", 0) or 0), 3),
            "end_s": round(float(ordered[tail].get("end", 0) or 0), 3),
            # ``end_s`` may include the first guest sentence used as a
            # punctuation tail. Keep the actual flagged-speaker end separate
            # for answer-length and interruption diagnostics.
            "question_end_s": round(float(
                ordered[question_tail if question and question_tail > last else last].get("end", 0) or 0
            ), 3),
            "words": words,
            "changes_subject": bool(shift or has_broadcast),
            "asks_a_whole_question": question,
            # A whole question opens a block however short it is; only an
            # incomplete aside is an interruption a cut may run through.
            "interjection": words <= INTERJECTION_MAX_WORDS and not shift and not question and not has_broadcast,
            # A long question is still the same subject being pressed. Only an
            # explicit change of subject closes a block: measured on a sabatina,
            # counting long follow-ups as boundaries cut two good clips in half.
            "major": bool(shift or has_broadcast),
            "broadcast_break": break_start,
            "broadcast_return": returned,
            "hard_boundary": bool(has_broadcast),
            "broadcast_boundary_kind": "break" if break_start else ("return" if returned else None),
            "text": text[:220],
            "provenance": "furia_interview_turns",
        })
    return turns


_VOCATIVE = None

# O nome do entrevistado, chamado de frente.
#
# É o sinal mais forte que existe numa entrevista, e o mais barato: quem
# apresenta diz "Renan," o tempo todo, e o entrevistado nunca diz o próprio
# nome em vocativo. Medido na sabatina da Band, era o que separava três dos
# cinco piores cortes entregues — inclusive o que abria em "Renan, eu preciso
# chamar aqui o nosso intervalo" e tirava a quarta melhor nota da rodada.
#
# Ficam de fora as menções em terceira pessoa ("o Renan disse", "com o Renan
# Santos"), que são gente FALANDO DELE, não COM ele: só conta o nome isolado
# por pontuação, que é a forma vocativa.
NOMES_DO_ENTREVISTADO = ("renan", "renan santos")

_NOME_VOCATIVO = None


def _regex_do_vocativo_por_nome(nomes: tuple[str, ...]) -> re.Pattern[str]:
    """Só chamar pelo nome conta. Nomear em terceira pessoa, não.

    A diferença é a mesma que o módulo já fazia para "candidato", e a armadilha
    é a mesma frase da abertura da sabatina:

        "o primeiro a detalhar suas propostas é o candidato do Missão,
         Renan Santos."

    O nome vem depois de uma vírgula e termina em ponto — só que ali ele é
    aposto, a âncora apresentando ao público, não alguém falando com ele.
    Contar isso punha a costura aos 31,6 s, dentro da leitura do estúdio.

    Duas formas sobrevivem, as duas inequívocas:

        "Renan, eu preciso chamar o intervalo."   nome ABRINDO a fala
        "..., e o que o senhor acha, Renan?"      nome FECHANDO a pergunta

    Aposto no meio de uma narração não bate em nenhuma das duas.
    """
    alternativas = "|".join(re.escape(nome) for nome in sorted(nomes, key=len, reverse=True))
    return re.compile(
        r"^\s(?:" + alternativas + r")\s*,"
        r"|[,;]\s*(?:" + alternativas + r")\s*[,;!?]"
        r"|,\s*(?:" + alternativas + r")\s*,"
    )


def addresses_the_guest(text: str, nomes: tuple[str, ...] = NOMES_DO_ENTREVISTADO) -> bool:
    """Whether the speaker is turning to the guest, not talking about him.

    "Candidato, boa noite" is the moment the programme hands over. "o candidato
    do Missão" and "o primeiro a detalhar suas propostas" are the anchor still
    presenting, in the third person, to the audience. Only the first marks where
    the interview actually begins.

    O nome próprio entra pela mesma porta e pela mesma regra: só na forma
    vocativa, isolado por pontuação.
    """
    global _VOCATIVE, _NOME_VOCATIVO
    if _VOCATIVE is None:
        _VOCATIVE = re.compile(
            r"(?:^\s*|[,;.!?]\s*)(?:candidato|senhor|senhora|deputado|governador)\s*[,?!.]"
        )
    normalizado = _normalize(text)
    if _VOCATIVE.search(normalizado):
        return True
    if not nomes:
        return False
    if nomes is NOMES_DO_ENTREVISTADO:
        if _NOME_VOCATIVO is None:
            _NOME_VOCATIVO = _regex_do_vocativo_por_nome(nomes)
        return bool(_NOME_VOCATIVO.search(normalizado))
    return bool(_regex_do_vocativo_por_nome(tuple(nomes)).search(normalizado))


def first_address_to_guest(sentences: list[dict[str, Any]]) -> float | None:
    """When the programme stops presenting itself and starts the interview.

    Read off the sentences rather than the turns: a turn can span the anchor's
    whole introduction, and what is wanted is the instant inside it where the
    programme hands over.
    """
    for item in sorted(sentences or [], key=lambda entry: float(entry.get("start", 0) or 0)):
        if addresses_the_guest(str(item.get("text") or "")):
            return float(item.get("start", 0) or 0)
    return None


def looks_like_an_interview(turns: list[dict[str, Any]], duration_s: float) -> bool:
    """Whether the source is a question-and-answer format at all.

    A live or a monologue produces almost no turns, and the seam rules must not
    fire there — on that material the boundaries come from the subject alone.
    Three turns in half an hour is the floor; below it the evidence is too thin
    to reshape anybody's cut.
    """
    if len(turns) < 3:
        return False
    if duration_s <= 0:
        return True
    # Roughly one turn every five minutes, which even a slow interview clears.
    return len(turns) >= max(3, duration_s / 300.0)
