"""Where a clip starts and stops, measured against two real failures.

Both come from one run of a 47-minute interview. The top-ranked clip opened on
the tail of a sentence — "você atender seus prazeres mais baixos" — when the
editor wanted it to open a few seconds later, on "O escândalo do Banco Master".
Another clip ended exactly on the interviewer's question, leaving the answer
outside it.
"""

from modules.clip_selector import ClipSelector


def _selector():
    return ClipSelector(min_duration=20, max_duration=180)


def test_clip_opening_mid_sentence_is_moved_to_the_next_real_sentence():
    clip = {
        "start": 729.5,
        "end": 864.4,
        # Roughly the density of real speech: about 18 characters per second.
        "text": (
            "você atender seus prazeres mais baixos. Não atua. O escândalo do Banco "
            "Master era basicamente sobre dinheiro e prazer sexual, não é isso? A elite "
            "política brasileira se baseia estritamente em dinheiro, troca de favores e "
            "prazer. " + "A boa liderança tem que ir para um outro caminho e isso exige sacrifício. " * 26
        ),
    }

    _selector()._trim_opening_fragment([clip])

    # "Não atua." is skipped too: opening on a two-word leftover reads as badly
    # as opening mid-sentence.
    assert clip["text"].startswith("O escândalo do Banco Master")
    assert 730.0 < clip["start"] < 736.0
    assert clip["opening_trimmed_s"] > 0


def test_a_clip_already_opening_on_a_sentence_is_left_alone():
    clip = {"start": 100.0, "end": 160.0, "text": "O escândalo do Banco Master era sobre dinheiro."}

    _selector()._trim_opening_fragment([clip])

    assert clip["start"] == 100.0
    assert "opening_trimmed_s" not in clip


def test_trimming_never_moves_the_start_beyond_its_ceiling():
    selector = _selector()
    # The first standalone sentence sits far into the window, so repairing the
    # boundary would hide a badly chosen window instead of fixing it.
    clip = {
        "start": 0.0,
        "end": 600.0,
        "text": "continuação arrastada sem fim. " + "Agora sim começa uma frase inteira e completa aqui. " * 40,
    }

    selector._trim_opening_fragment([clip])

    assert clip["start"] == 0.0 or clip["opening_trimmed_s"] <= selector.MAX_OPENING_TRIM_S


def test_clip_ending_on_a_question_is_extended_into_the_answer():
    sentences = [
        {"start": 623.1, "end": 629.2, "text": "O que faria a pessoa física, Renan Santos, votar no candidato Renan Santos?"},
        {"start": 629.2, "end": 634.5, "text": "Eh, infelizmente tem que recorrer à resposta anterior, ser um bom líder."},
        {"start": 634.5, "end": 642.5, "text": "Ser um bom líder e ter tomado as decisões duras que machucaram meu grupo político."},
    ]
    clip = {
        "start": 561.8,
        "end": 630.0,
        "text": "Fizemos uma sondagem. O que faria a pessoa física, Renan Santos, votar no candidato Renan Santos?",
    }

    _selector()._close_open_question([clip], sentences)

    assert clip["end"] > 630.0
    assert clip["answer_extended_s"] > 0
    assert clip["duration"] == round(clip["end"] - 561.8, 3)


def test_a_question_with_nothing_following_is_left_untouched():
    """Extending into a distant sentence would splice unrelated material."""
    sentences = [{"start": 700.0, "end": 712.0, "text": "Assunto completamente diferente começa muito depois."}]
    clip = {"start": 561.8, "end": 630.0, "text": "E o senhor, como responde a isso?"}

    _selector()._close_open_question([clip], sentences)

    assert clip["end"] == 630.0
    assert "answer_extended_s" not in clip


def test_a_clip_not_ending_on_a_question_is_left_untouched():
    sentences = [{"start": 630.0, "end": 640.0, "text": "Uma frase qualquer que vem depois do corte."}]
    clip = {"start": 561.8, "end": 630.0, "text": "O corte termina com uma afirmação completa."}

    _selector()._close_open_question([clip], sentences)

    assert clip["end"] == 630.0
