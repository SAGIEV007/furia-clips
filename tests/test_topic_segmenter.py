"""Furia's own reading of a long transcript, with no Acervo snapshot present.

Measured against the blocks the Acervo labelled on two real sources: 23/27 blocks
covered on the source used for calibration and 9/11 on a source never used for it,
with 72% and 81% of the detected time falling inside a real block.
"""

from modules.non_content_detector import (
    LEARNED_NON_CONTENT_THRESHOLD,
    detect_non_content_regions,
    score_segment,
)
from modules.topic_segmenter import cohesion_curve, segment_transcript


def _talk(start, texts, step=4.0):
    return [
        {"start": start + index * step, "end": start + (index + 1) * step, "text": text}
        for index, text in enumerate(texts)
    ]


def _subject(term, other, count):
    """Sentences that keep returning to one subject without repeating verbatim.

    Real speech develops a subject with varied wording; identical sentences would
    read as a chanted jingle, which is a different thing entirely.
    """
    shapes = [
        "O {t} precisa de {o} para funcionar no estado {n}.",
        "Quem defende {o} entende que o {t} mudou depois de {n} anos.",
        "A discussão sobre {t} passa por {o} e pelo orçamento de {n} bilhões.",
        "Sem {o}, o {t} segue travado em {n} municípios do país.",
        "Nosso projeto de {t} trata {o} como prioridade número {n}.",
        "Ninguém explicou por que {o} ficou fora do {t} durante {n} anos.",
        "Com {o} resolvido, o {t} deixa de custar {n} vezes mais caro.",
    ]
    return [
        shapes[index % len(shapes)].format(t=term, o=other, n=index + 3)
        for index in range(count)
    ]


def test_cohesion_drops_where_the_subject_changes():
    segments = _talk(0.0, _subject("imposto", "reforma", 40) + _subject("futebol", "estádio", 40))

    curve = cohesion_curve(segments, window=6)
    middle = len(curve) // 2
    # The valley sits at the change of subject, not inside either half.
    assert min(curve[middle - 3:middle + 3]) < sum(curve) / len(curve)


def test_two_subjects_become_two_units():
    segments = _talk(0.0, _subject("imposto", "reforma", 60) + _subject("segurança", "polícia", 60))

    units = segment_transcript(segments, min_sentences=32)

    assert len(units) == 2
    assert "imposto" in units[0]["topic_terms"]
    assert "segurança" in units[1]["topic_terms"]
    assert units[0]["end_s"] <= units[1]["start_s"]
    assert all(unit["provenance"] == "furia_topic_segmenter" for unit in units)


def test_a_developed_subject_is_marked_as_carrying_one():
    segments = _talk(0.0, _subject("imposto", "reforma", 80))

    units = segment_transcript(segments, min_sentences=32)

    assert units
    assert units[0]["carries_subject"] is True
    assert units[0]["recurrence"] >= 0.2


def test_a_transcript_too_short_to_segment_returns_nothing():
    assert segment_transcript(_talk(0.0, ["uma frase só"]), min_sentences=32) == []
    assert segment_transcript([], min_sentences=32) == []


def test_engagement_requests_read_as_non_content():
    verdict = score_segment("Vamos dando like na live aqui pra gente chegar a 14 mil inscritos.")

    assert verdict["non_content"] is True
    assert "engajamento" in verdict["cues"]


def test_unintelligible_caption_reads_as_non_content():
    # A real labelled region of one source was exactly this: caption noise where
    # no intelligible speech existed.
    verdict = score_segment("เฮ เฮ")

    assert verdict["non_content"] is True
    assert "ininteligivel" in verdict["cues"]


def test_an_argument_is_not_mistaken_for_filler():
    verdict = score_segment(
        "A proposta endurece a lei penal porque o crime organizado tomou territórios "
        "inteiros e o Estado precisa retomá-los com presença permanente."
    )

    assert verdict["non_content"] is False
    assert verdict["cues"] == []


def test_detected_regions_carry_a_readable_reason():
    segments = _talk(0.0, ["Vamos dando like na live e se inscreve no canal agora."] * 6)

    regions = detect_non_content_regions(segments)

    assert regions
    assert regions[0]["reason"].startswith("Sem conteúdo editorial:")
    assert regions[0]["provenance"] == "furia_local_detector"


def test_learned_lexicon_separates_a_sponsor_read_from_an_argument():
    """The distilled odds decide, after a measurement that overturned an earlier one.

    Cycle 23 concluded the learned score could not discriminate and kept it out
    of the verdict. That conclusion held for an 86-term lexicon scored as a mean
    over sliding windows. Extending the vocabulary to the whole promotional,
    production and sign-off surface changed the picture on real material: the
    sponsor read of a 47-minute interview scores 0.58 and the closing thanks
    0.389, while four passages of actual argument from the same interview score
    exactly 0. The threshold sits in that gap.
    """
    sponsor = score_segment(
        "Assinar o nosso combo significa ter os bastidores de Brasília em tempo real. "
        "Preparamos uma condição exclusiva para o nosso público do YouTube. Clique no "
        "link aqui embaixo na descrição ou aponte a câmera para o QR code na tela."
    )
    argument = score_segment(
        "Eu acho que uma das perspectivas de direito penal que a gente tem que trazer é "
        "o direito penal voltado pra vítima. A vítima só vai entender que o pacto social "
        "é válido se ela se sentir contemplada através do senso de justiça."
    )

    assert sponsor["non_content"] is True
    assert "lexico_aprendido" in sponsor["cues"]
    assert sponsor["learned_score"] >= LEARNED_NON_CONTENT_THRESHOLD

    # Real argument must stay untouched: discarding speech is worse than keeping
    # a weak candidate, and this passage carries no promotional vocabulary at all.
    assert argument["non_content"] is False
    assert argument["learned_score"] == 0.0


def test_closing_thanks_are_recognised_as_filler():
    verdict = score_segment(
        "Muito obrigado aí pela oportunidade. Eu queria primeiro agradecer assim a honra "
        "incrível de estar aqui presente. Obrigado."
    )

    assert verdict["non_content"] is True


def test_priors_file_ships_with_the_repository():
    from modules.non_content_detector import load_priors

    priors = load_priors()
    assert priors["schema_version"] == "chub-priors-v2"
    assert len(priors["non_content_terms"]) >= 200
    assert priors["structure"]["block_duration_s"]["median"] > 0
    # Aggregate statistics only: no transcript, URL or personal data travels.
    assert "não reversível" in priors["provenance"]["privacy"]


def test_campaign_vocabulary_alone_never_discards_editorial_content():
    """The lexicon corroborates; it does not convict on its own.

    Three stretches of a 98-minute live were discarded by an earlier version on
    the learned score alone, and all three sit inside blocks the Acervo endorsed
    as editorial: Renan describing the campaign app, the origin story of the
    party, and the vote codes. The words that fired — "app", "org", "live",
    "chat", "códigos" — belong to the subject as much as to the filler.
    """
    # Verbatim from the live, at 4897s, inside the block the Acervo titled
    # "Partido Missão mobiliza ato na USP". An invented sentence packed with
    # campaign words scores far denser than real speech and would prove nothing.
    campanha = score_segment(
        "Vamos todo mundo começar. Agora começou a guerra. Quase 40.000. Dá para chegar "
        "até minha com 50.000. Vamos fazer 50.000 1000 pessoas no aplicativo. Como é que "
        "faz para baixar? app.org.br. app.missão.org.br. app.missão.org.br. Vamos todo "
        "mundo baixar o aplicativo, tá? E aí já tem aí vai tem o codigozinho que precisa. "
        "Qual é? 14. Como? Voto 14. Então, olha só."
    )

    assert campanha["learned_score"] >= LEARNED_NON_CONTENT_THRESHOLD
    assert campanha["cues"] == ["lexico_aprendido"]
    assert campanha["non_content"] is False


def test_a_sponsor_read_still_convicts_on_the_lexicon_alone():
    from modules.non_content_detector import LEARNED_NON_CONTENT_DECISIVE

    anuncio = score_segment(
        "Assinar o nosso combo significa ter os bastidores em tempo real. Preparamos uma "
        "condição exclusiva para o nosso público do YouTube. Clique no link aqui embaixo na "
        "descrição ou aponte a câmera para o QR code na tela. Assine o combo agora."
    )

    assert anuncio["learned_score"] >= LEARNED_NON_CONTENT_DECISIVE
    assert anuncio["non_content"] is True


def test_two_weak_cues_together_still_convict():
    pedido = score_segment(
        "Vamos dando like na live aqui pra gente chegar a 14 mil, bora galera, "
        "a transmissão tá bombando, bora compartilhar a live."
    )

    assert len(pedido["cues"]) >= 2
    assert pedido["non_content"] is True
