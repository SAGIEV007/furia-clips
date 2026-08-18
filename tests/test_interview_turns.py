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


def test_a_clip_that_carries_question_and_answer_validates_its_own_bridge():
    """The gate that held back fourteen of nineteen candidates.

    A clip is refused when a question is heard and the bridge to its answer was
    never validated. Validation used to require the clip to line up, edge to
    edge, with a question-and-answer window computed in the context stage — which
    a selected window almost never does. On the sabatina that left only the five
    candidates containing no question at all, which is precisely the shape the
    editor complained about: the middle and the end of an answer, never the
    question that provoked it.
    """
    selector = ClipSelector()
    clip = {}
    turns = detect_interviewer_turns(SEGURANCA)

    selector._mark_local_qa_bridge(clip, 450.0, 520.0, turns, SEGURANCA)

    assert clip["qa_bridge_local"] is True
    assert clip["qa_boundary_basis_local"] == "turnos_do_entrevistador"
    assert clip["qa_bridge_answer_words"] >= 12


def test_the_bridge_needs_the_answer_and_not_only_the_question():
    """A question with nothing after it is the dangling clip the gate exists for."""
    selector = ClipSelector()
    clip = {}
    turns = detect_interviewer_turns(SEGURANCA)

    selector._mark_local_qa_bridge(clip, 450.0, 472.0, turns, SEGURANCA)

    assert clip == {}


def test_local_evidence_reaches_the_gate_when_the_context_stage_produced_nothing():
    from modules.editorial_chapters import annotate_clip_with_chapters

    annotated = annotate_clip_with_chapters(
        {"start": 450.0, "end": 520.0, "qa_bridge_local": True}, {}
    )

    assert annotated["qa_bridge"] is True
    assert annotated["qa_boundary_basis"] == "turnos_do_entrevistador"


def test_candidates_are_born_on_the_seams_instead_of_a_stopwatch():
    """Where the "todos pequenos" complaint came from.

    Blocks used to be closed every eighteen to thirty seconds, wherever that
    landed. On the 31-minute sabatina that produced 89 tiles with a median of
    20 seconds, five of which happened to start within two seconds of a real
    boundary. Cutting on the seams of the conversation instead gives 24 blocks
    with a median of 67 seconds, ten of them starting on a real boundary.
    """
    selector = ClipSelector()

    seam_blocks = selector._build_transcript_blocks(SEGURANCA)
    timed_blocks = selector._timed_transcript_blocks(SEGURANCA)

    assert seam_blocks
    # The exchange survives as one unit instead of being closed by the clock.
    assert len(seam_blocks) < len(timed_blocks)
    starts = [block["start"] for block in seam_blocks]
    assert 453.6 in starts


def test_a_source_with_no_conversation_keeps_the_timed_blocks():
    selector = ClipSelector()
    live = _talk([(index * 20.0, index * 20.0 + 20.0, f"Vamos todo mundo baixar o aplicativo, número {index}.")
                  for index in range(12)])

    assert selector._conversation_seams(live) == []
    assert selector._build_transcript_blocks(live) == selector._timed_transcript_blocks(live)


def test_an_exchange_longer_than_a_clip_is_divided_at_sentences():
    selector = ClipSelector()
    long_answer = SEGURANCA + _talk([
        (700.0 + index * 30.0, 730.0 + index * 30.0, f"Sigo explicando o mesmo ponto pela vez número {index}.")
        for index in range(10)
    ])

    blocks = selector._build_transcript_blocks(long_answer)

    assert blocks
    assert all(block["end"] - block["start"] <= selector.preferred_max_duration + 40 for block in blocks)


def test_an_imported_caption_is_broken_back_into_sentences():
    """Where the whole turn machinery went silent on a real run.

    A 31-minute sabatina imported as 62 caption segments produced sentences of
    forty seconds, each holding a question and its answer in one lump. The
    detector found five turns instead of nineteen and the source was not even
    recognised as an interview, so every seam rule sat idle.
    """
    selector = ClipSelector()
    lump = [{
        "start": 440.0,
        "end": 480.0,
        "text": (
            "O estado brasileiro se torna uma inutilidade que só cobra impostos. "
            "Candidato, eu queria continuar nesse tema da segurança pública. "
            "Há uma discussão muito grande hoje em torno das facções criminosas."
        ),
    }]

    pieces = selector._split_long_segments(lump)

    assert len(pieces) == 3
    assert pieces[1]["text"].startswith("Candidato")
    # Times are shared out and stay inside the original span, in order.
    assert pieces[0]["start"] == 440.0
    assert pieces[-1]["end"] <= 480.0
    assert pieces[0]["end"] <= pieces[1]["start"] + 0.01 <= pieces[1]["end"]


def test_a_short_segment_is_left_whole():
    selector = ClipSelector()
    short = [{"start": 10.0, "end": 14.0, "text": "Nunca. Eu acho isso humilhante."}]

    assert selector._split_long_segments(short) == short


def test_the_studio_opening_is_not_a_clip():
    """The anchor reading the running order before the guest has said anything.

    Verbatim from the top of the sabatina, where one run rendered fifty-two
    seconds of the studio introducing the programme as its fifth clip.
    """
    selector = ClipSelector()
    abertura = _talk([
        (7.0, 24.0, "O jornal do SBT News está de volta com o início das sabatinas."),
        (24.0, 31.6, "Os seis candidatos mais bem colocados serão entrevistados nesta semana."),
        (31.6, 44.2, "De acordo com o sorteio, o primeiro a detalhar suas propostas é o candidato do Missão."),
        (44.2, 51.6, "Candidato, boa noite, obrigado por estar com a gente."),
        (51.6, 59.2, "A gente começa falando de segurança pública, com o senhor."),
        (59.2, 90.0, "Boa noite. O Brasil tem uma das maiores populações carcerárias do mundo."),
        (300.0, 330.0, "Mas o senhor defende ampliar as prisões e construir superpresídios?"),
        (330.0, 360.0, "Defendo, porque a punição hoje é baixa demais para o crime violento."),
        (600.0, 630.0, "Candidato, eu queria continuar nesse tema da segurança pública."),
        (630.0, 660.0, "Pode perguntar, estou à disposição para detalhar a proposta."),
    ])

    clips = selector._align_to_interview_turns(
        [{"start": 7.0, "end": 59.2, "text": "..."}], abertura
    )

    assert clips == []
