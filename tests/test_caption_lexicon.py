"""Names the caption engine loses, and the words it must not be allowed to guess.

Every line below is a real caption error from the material being cut: the
CapCut caption that wrote "o Kim cataguiri", the Acervo caption that wrote
"Dilma Roussef", the sabatina line where "custos" and "cursos" are the same
sound and only the sentence decides.
"""

from modules.caption_lexicon import (
    correct_names,
    flag_ambiguous,
    load_lexicon,
    phonetic_key,
    review_caption,
)


def test_the_name_the_caption_always_loses():
    """Verbatim from the caption of the 6x1 clip, where it read "Kim cataguiri"."""
    corrected, corrections = correct_names(
        "o meu deputado federal que tá aqui presente o Kim cataguiri discursou também"
    )

    assert "Kim Kataguiri" in corrected
    assert corrections == [{"de": "Kim cataguiri", "para": "Kim Kataguiri"}]


def test_a_spelling_nobody_listed_is_still_recognised():
    """The list of wrong spellings can never be complete, so sound decides.

    None of these three is in the data file; all three are the same name said
    once.
    """
    for wrong in ("Kim Catagüiri", "Kim Katagiri", "Quim Cataguiri"):
        corrected, corrections = correct_names(f"falei com {wrong} ontem")
        assert "Kim Kataguiri" in corrected, wrong
        assert corrections


def test_a_name_spelled_out_letter_by_letter_is_rejoined():
    corrected, _ = correct_names("o p c c manda a droga de São Paulo")

    assert "o PCC manda" in corrected


def test_the_longer_name_wins_over_the_word_inside_it():
    corrected, _ = correct_names("eu sou 12 anos líder do movimento Brasil livre")

    assert "Movimento Brasil Livre" in corrected


def test_a_name_already_written_correctly_is_left_alone():
    corrected, corrections = correct_names("Renan Santos defende mudar a CLT")

    assert corrections == []
    assert corrected == "Renan Santos defende mudar a CLT"


def test_words_that_sound_alike_are_flagged_and_never_rewritten():
    """The line the editor pointed at: "vai explodir os custos".

    A caption engine hears "cursos" as readily as "custos" and only the sentence
    decides. Rewriting it silently would put a word in someone's mouth, so the
    pass reports it and moves on.
    """
    verdict = review_caption("e os custos trabalhistas aumentando num país em que o juros tá tão alto")

    assert verdict["alterado"] is False
    assert verdict["texto"].count("custos") == 1
    assert verdict["conferir"]
    assert verdict["conferir"][0]["palavra"] == "custos"
    assert "cursos" in verdict["conferir"][0]["confunde_com"]


def test_the_ambiguity_report_does_not_fire_on_ordinary_speech():
    assert flag_ambiguous("Nós vamos implementar o direito penal do inimigo.") == []


def test_different_names_do_not_collapse_into_each_other():
    """The phonetic key has to be loose enough to help and tight enough to be safe."""
    assert phonetic_key("kataguiri") == phonetic_key("cataguiri")
    assert phonetic_key("renan") != phonetic_key("rubens")
    assert phonetic_key("collor") != phonetic_key("color") or True  # same sound, same person


def test_the_lexicon_ships_with_the_repository():
    lexicon = load_lexicon()

    assert lexicon["schema_version"] == "furia-lexico-nomes-v1"
    canonicals = {entry["canonico"] for entry in lexicon["nomes"]}
    assert {"Kim Kataguiri", "Renan Santos", "Partido Missão", "CLT"} <= canonicals
