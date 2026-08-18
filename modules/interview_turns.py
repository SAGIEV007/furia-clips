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

import unicodedata
from typing import Any


# Second person formal, and the possessives that go with it. The guest answers
# in the first person and addresses the room as "você"; these forms belong to
# whoever is questioning him.
_ADDRESS = (
    " o senhor ", " ao senhor ", " do senhor ", " pro senhor ", " para o senhor ",
    " senhor ", " candidato", " deputado ", " governador ", " presidente eleito",
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
# Consecutive flagged sentences this close together are one turn, not several.
_TURN_GAP_SENTENCES = 3


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFC", str(text or "")).lower().replace("ç", "c")
    return " " + " ".join(lowered.split()) + " "


def is_interviewer_sentence(text: str) -> bool:
    """True when this sentence is the interviewer speaking, not the guest."""
    normalized = _normalize(text)
    return any(k in normalized for k in _ADDRESS) or any(k in normalized for k in _ASKS)


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
        if groups and index - groups[-1][-1] <= _TURN_GAP_SENTENCES:
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
