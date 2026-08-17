"""Furia's own reading of a long transcript, with no Acervo snapshot present.

Measured against the blocks the Acervo labelled on two real sources: 23/27 blocks
covered on the source used for calibration and 9/11 on a source never used for it,
with 72% and 81% of the detected time falling inside a real block.
"""

from modules.non_content_detector import detect_non_content_regions, score_segment
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


def test_learned_priors_are_reported_but_never_decide():
    """The distilled odds travel as evidence, not as a verdict.

    Measured on two labelled sources, the aggregated score does not separate
    content from non-content: on the 98-minute live the content units scored
    higher than the non-content ones. Letting it flip the verdict would discard
    real speech on a signal that was shown not to discriminate.
    """
    promotional = score_segment("Acesse o link na descrição e use o cupom de desconto do nosso patrocinador.")
    argument = score_segment(
        "A proposta reduz a pena mínima porque o presídio virou escritório do crime organizado."
    )

    # The odds do fire on promotional vocabulary...
    assert promotional["learned_score"] > argument["learned_score"]
    assert promotional["learned_terms"]
    # ...but no cue named after them exists, and the verdict ignores the score.
    assert "lexico_aprendido" not in promotional["cues"]
    assert argument["non_content"] is False


def test_priors_file_ships_with_the_repository():
    from modules.non_content_detector import load_priors

    priors = load_priors()
    assert priors["schema_version"] == "chub-priors-v1"
    assert len(priors["non_content_terms"]) >= 50
    assert priors["structure"]["block_duration_s"]["median"] > 0
    # Aggregate statistics only: no transcript, URL or personal data travels.
    assert "não reversível" in priors["provenance"]["privacy"]
