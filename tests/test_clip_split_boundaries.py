"""Where an over-long exchange gets cut in two.

Measured on the press conference of 18/08/2026 (73 minutes, Instituto Unidos
Brasil). The seam detection found only fourteen conversational seams on that
source, so the blocks between them ran far past what a clip can hold — and the
splitter closed each piece the instant the stopwatch hit the preferred ceiling.

The result was four candidates of exactly 180.0 seconds, three of which were
consecutive tiles of a single answer: 1137→1158, 1158→1227, 1227→1407. The
editor read them as random, and was right to: each opened mid-argument and
stopped mid-argument, and the second was, in their words, "just the beginning
of" the third.
"""

from modules.clip_selector import ClipSelector


def _sentences(rows):
    return [{"start": start, "end": end, "text": text} for start, end, text in rows]


def _selector():
    # O teto vai explícito. Estes testes medem *onde* a peça fecha dentro da
    # janela — na troca de locutor, na pausa —, não qual deve ser o tamanho da
    # janela. Esse tamanho é medido por `scripts/medir_cortes.py` contra as
    # fronteiras humanas do Acervo, e amarrar a fixture ao padrão faria estes
    # testes quebrarem toda vez que a régua o movesse, sem que o mecanismo aqui
    # tivesse mudado. A fixture tem a troca de locutor aos 160 s.
    return ClipSelector(
        target_duration=45, max_clips=10, min_duration=20,
        max_duration=600, preferred_max_duration=180.0,
    )


# One long answer with a clear break in it: a two-second silence at 150s, and
# the interviewer taking the floor again at 200s.
LONG_ANSWER = _sentences(
    [(index * 10.0, index * 10.0 + 9.0, f"Frase corrida número {index} do mesmo argumento.") for index in range(15)]
    + [(150.0, 158.0, "E é por isso que o Estado falhou com essa gente.")]
    + [(160.0, 169.0, "Agora, candidato, eu queria mudar de assunto e falar de economia.")]
    + [(index * 10.0, index * 10.0 + 9.0, f"Resposta sobre economia, parte {index}.") for index in range(17, 32)]
)


def test_a_long_block_is_not_cut_by_the_stopwatch():
    """The defect itself: pieces landing on the ceiling to the tenth of a second."""
    pieces = _selector()._split_to_clip_length(LONG_ANSWER)

    assert len(pieces) > 1
    for piece in pieces:
        span = piece[-1]["end"] - piece[0]["start"]
        assert span <= 180.0
    spans = [round(piece[-1]["end"] - piece[0]["start"], 1) for piece in pieces[:-1]]
    assert 180.0 not in spans, f"peça fechada no teto do cronômetro: {spans}"


def test_the_cut_falls_where_the_interviewer_takes_the_floor():
    """A change of speaker is a real boundary and beats any pause."""
    pieces = _selector()._split_to_clip_length(LONG_ANSWER)

    assert pieces[1][0]["text"].startswith("Agora, candidato")


def test_a_block_that_already_fits_is_left_alone():
    short = _sentences([(0.0, 40.0, "Uma ideia inteira."), (40.0, 90.0, "E a conclusão dela.")])

    assert _selector()._split_to_clip_length(short) == [short]


def test_no_piece_is_too_short_to_be_a_clip():
    pieces = _selector()._split_to_clip_length(LONG_ANSWER)

    for piece in pieces:
        assert piece[-1]["end"] - piece[0]["start"] >= 20.0


# ── Vizinhos ──────────────────────────────────────────────────────────────────

def _clip(start, end, score):
    return {"start": start, "end": end, "viral_score": score, "text": "trecho"}


def test_a_clip_that_only_continues_another_is_dropped():
    """1137→1158, 1158→1227 and 1227→1407 went out as three separate files."""
    selector = _selector()
    kept = selector._drop_touching_siblings([
        _clip(1137.5, 1157.8, 68),
        _clip(1157.8, 1227.2, 82),
        _clip(1227.2, 1407.2, 85),
    ])

    assert len(kept) == 1
    assert kept[0]["start"] == 1227.2


def test_clips_far_apart_are_both_kept():
    selector = _selector()
    kept = selector._drop_touching_siblings([_clip(100.0, 160.0, 80), _clip(900.0, 980.0, 70)])

    assert len(kept) == 2


def test_overlap_is_left_to_the_pass_that_owns_it():
    """Overlapping candidates have their own handling and their own counters."""
    selector = _selector()
    kept = selector._drop_touching_siblings([_clip(0.0, 30.0, 90), _clip(10.0, 40.0, 60)])

    assert len(kept) == 2
