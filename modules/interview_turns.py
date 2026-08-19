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
    " o senhor ", " ao senhor ", " do senhor ", " pro senhor ", " para o senhor ",
    " senhor ", " deputado ", " governador ", " presidente eleito",
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

# Below this a turn is an interruption inside the answer, not a new question:
# "Senhor manter então para a extrema pobreza até fazer a transição." The guest
# resumes the same argument straight after, so a cut may run through it.
INTERJECTION_MAX_WORDS = 12
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

    flagged = [index for index, item in enumerate(ordered) if is_interviewer_sentence(item["text"])]
    if not flagged:
        return []

    groups: list[list[int]] = []
    for index in flagged:
        near_in_order = bool(groups) and index - groups[-1][-1] <= _TURN_GAP_SENTENCES
        # Proximity in the transcript is not proximity in time. On a source
        # transcribed in long segments, two questions five minutes apart can sit
        # three sentences apart, and merging them produced a single "turn"
        # spanning the whole interview.
        near_in_time = bool(groups) and (
            float(ordered[index].get("start", 0) or 0)
            - float(ordered[groups[-1][-1]].get("end", 0) or 0)
        ) <= _TURN_GAP_SECONDS
        if near_in_order and near_in_time:
            groups[-1].append(index)
        else:
            groups.append([index])

    turns: list[dict[str, Any]] = []
    for group in groups:
        first, last = group[0], group[-1]
        # The turn usually spills one sentence past the last flagged one, where
        # the actual question mark lands.
        tail = min(len(ordered) - 1, last + 1)
        spoken = " ".join(str(ordered[i].get("text") or "") for i in range(first, last + 1))
        text = " ".join(str(ordered[i].get("text") or "") for i in range(first, tail + 1))
        # Only the sentences actually recognised as the interviewer's count
        # towards the length: the sentence after them is usually the guest
        # already answering, and including it inflates every short aside into a
        # question of its own.
        words = len(spoken.split())
        shift = any(k in _normalize(text) for k in _SHIFT)
        turns.append({
            "start_s": round(float(ordered[first].get("start", 0) or 0), 3),
            "end_s": round(float(ordered[tail].get("end", 0) or 0), 3),
            "words": words,
            "changes_subject": shift,
            "interjection": words <= INTERJECTION_MAX_WORDS and not shift,
            # A long question is still the same subject being pressed. Only an
            # explicit change of subject closes a block: measured on a sabatina,
            # counting long follow-ups as boundaries cut two good clips in half.
            "major": shift,
            "text": text[:220],
            "provenance": "furia_interview_turns",
        })
    return turns


_VOCATIVE = None


def addresses_the_guest(text: str) -> bool:
    """Whether the speaker is turning to the guest, not talking about him.

    "Candidato, boa noite" is the moment the programme hands over. "o candidato
    do Missão" and "o primeiro a detalhar suas propostas" are the anchor still
    presenting, in the third person, to the audience. Only the first marks where
    the interview actually begins.
    """
    global _VOCATIVE
    if _VOCATIVE is None:
        _VOCATIVE = re.compile(
            r"(?:^\s*|[,;.!?]\s*)(?:candidato|senhor|senhora|deputado|governador)\s*[,?!.]"
        )
    return bool(_VOCATIVE.search(_normalize(text)))


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
