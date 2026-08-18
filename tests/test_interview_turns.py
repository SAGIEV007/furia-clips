"""Boundaries of a clip cut from an interview, measured against a real sabatina.

Every sentence below is verbatim from the SBT sabatina of 17/08/2026, the source
whose sixteen rendered clips the editor reviewed one by one. Invented dialogue
would prove nothing here: the detector reads forms of address that only real
speech distributes correctly between interviewer and guest.

On that source the Acervo published fourteen blocks and every one of them opens
on an interviewer turn. Before this pass, none of the sixteen clips ended within
two seconds of one of those boundaries and six ran across one; after it, ten of
fifteen end on a boundary and none crosses a change of subject.
"""

from modules.clip_selector import ClipSelector
from modules.interview_turns import (
    detect_interviewer_turns,
    is_interviewer_sentence,
    looks_like_an_interview,
)


def _talk(rows):
    """Sentences as the selector receives them: start, end, text."""
    return [{"start": start, "end": end, "text": text} for start, end, text in rows]


# The seam at 07:33.68 of the sabatina: the reporter takes the floor back and
# announces she is staying on the same theme, which closed the block about
# prisons and opened the one about foreign intervention.
SEGURANCA = _talk([
    (440.0, 443.1, "Esse cara vai ficar muito tempo, esse cara não vai ver mais a juventude dele."),
    (443.1, 450.2, "Se eu não entregar o senso de justiça para as pessoas, de que serve o estado?"),
    (450.2, 453.6, "O estado brasileiro se torna uma inutilidade que só cobra impostos."),
    (453.6, 456.8, "Candidato, eu queria continuar nesse tema da segurança pública."),
    (456.8, 463.8, "Há uma discussão muito grande hoje em torno das facções criminosas."),
    (463.8, 471.2, "Eu te pergunto, o senhor é favorável a ações militares norte-americanas?"),
    (493.0, 496.4, "Nunca. Eu acho isso humilhante pra gente."),
    (496.9, 498.4, "O Brasil tem todas as condições."),
    (513.4, 516.0, "A gente tem que ter acordo de cooperação com os Estados Unidos da América."),
    (531.4, 534.4, "Agora, quem vai destruir o crime no Brasil tem que ser o Brasil."),
    (617.4, 621.0, "Agora, candidato, seguindo nessa linha de raciocínio, eu quero falar sobre Bolsa Família."),
    (621.0, 626.0, "As punições do Brasil são muito baixas, são muito pequenas."),
    (626.0, 632.0, "Quem colabora com facção tem que responder como faccionado."),
    (632.0, 638.0, "Isso vale para o agente público e para quem está fora do estado."),
    (666.9, 670.0, "O senhor vai enfrentar o Congresso para fazer o que está prometendo no seu plano de governo."),
    (670.0, 675.0, "É exatamente isso que a gente vai enfrentar com inteligência."),
])


def test_the_interviewer_is_recognised_and_the_guest_is_not():
    assert is_interviewer_sentence("Candidato, eu queria continuar nesse tema da segurança pública.")
    assert is_interviewer_sentence("Mas o senhor enfrenta vários processos judiciais ligados às empresas?")

    # The guest speaks in the first person and never addresses himself formally.
    # "eu quero" belongs to him as often as to a question, which is why it is not
    # a marker: he says it constantly.
    assert not is_interviewer_sentence("Nós vamos implementar o direito penal do inimigo.")
    assert not is_interviewer_sentence(
        "porque eu quero que a família daquela criança saiba que o estado agiu."
    )
    assert not is_interviewer_sentence("O Brasil tem todas as condições.")


def test_a_change_of_subject_is_told_apart_from_pressing_the_same_one():
    turns = detect_interviewer_turns(SEGURANCA)

    assert turns
    opening = turns[0]
    assert opening["start_s"] == 453.6
    assert opening["changes_subject"] is True
    assert opening["major"] is True


def test_a_short_aside_is_not_a_seam():
    """The reporter interrupts, the guest carries on with the same argument.

    Ending a clip here is what turned an answer about replacing Bolsa Família
    into a clip that read as a promise to keep people in extreme poverty: the
    part that resolved it came after the interruption.
    """
    aside = detect_interviewer_turns(_talk([
        (1650.0, 1653.4, "Eu não vou deixar ninguém que tá no município que tem bolsa família morrer de fome."),
        (1673.4, 1676.6, "Senhor manter então para a extrema pobreza até fazer a transição."),
        (1676.6, 1681.0, "Vou manter, e quem não quiser frente de trabalho não vai ter o benefício."),
    ]))

    assert len(aside) == 1
    assert aside[0]["interjection"] is True
    assert aside[0]["major"] is False


def test_a_live_is_not_an_interview():
    live = _talk([
        (0.0, 4.0, "Vamos todo mundo começar, agora começou a guerra."),
        (4.0, 8.0, "Dá para chegar a 50.000 pessoas no aplicativo."),
        (8.0, 12.0, "Como é que faz para baixar? app.missão.org.br."),
    ])

    assert looks_like_an_interview(detect_interviewer_turns(live), 5400.0) is False


def test_a_clip_stops_where_the_reporter_takes_the_floor_back():
    """The complaint was exact: the clip ran to 1:32 and was usable to 1:12.

    1:12 into that clip is 07:33.68 of the source — the sentence where the
    reporter starts the next question, and the boundary the Acervo drew.
    """
    selector = ClipSelector()
    clips = selector._align_to_interview_turns(
        [{"start": 380.0, "end": 472.0, "text": "..."}], SEGURANCA
    )

    assert len(clips) == 1
    assert clips[0]["end"] == 453.6
    assert clips[0]["turn_aligned"]["end_shift_s"] < 0
    assert clips[0]["turn_aligned"]["crossed_subject_change"] is True


def test_a_clip_that_stops_before_the_answer_arrives_is_extended():
    selector = ClipSelector()
    clips = selector._align_to_interview_turns(
        [{"start": 496.9, "end": 600.0, "text": "..."}], SEGURANCA
    )

    assert len(clips) == 1
    # Nothing of the answer is left outside: the window reaches the next seam.
    assert clips[0]["end"] == 617.4
    assert clips[0]["turn_aligned"]["end_shift_s"] > 0


def test_a_stub_left_by_a_change_of_subject_is_discarded():
    """A window whose material mostly lives past the seam is not a clip.

    This is the shape of the candidate the fallback produced at 13:22 of the
    sabatina: fifty seconds chosen, of which only eight sat before the reporter
    changed the subject. Truncating it leaves a stub, and there is no minimum
    number of clips to reach, so it is dropped instead of rendered short.
    """
    selector = ClipSelector()
    clips = selector._align_to_interview_turns(
        [{"start": 440.0, "end": 540.0, "text": "..."}], SEGURANCA
    )

    assert clips == []


def test_boundaries_are_left_alone_when_the_source_is_not_an_interview():
    selector = ClipSelector()
    live = _talk([
        (0.0, 30.0, "Vamos todo mundo começar, agora começou a guerra."),
        (30.0, 60.0, "Dá para chegar a 50.000 pessoas no aplicativo."),
    ])
    original = {"start": 5.0, "end": 40.0, "text": "..."}

    clips = selector._align_to_interview_turns([dict(original)], live)

    assert clips == [original]
