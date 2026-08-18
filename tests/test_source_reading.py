"""The reading the operator sees before any clip is cut.

Measured on the SBT sabatina of 17/08/2026. Reading the transcript alone, Furia
finds eight stretches covering 99% of the source, and six of its eight boundaries
fall exactly on a boundary the Acervo published. With the reviewed blocks present
the reading is theirs instead: fourteen stretches, each with a title somebody
wrote and the strong moments inside it.
"""

from modules.source_reading import read_source


def _talk(rows):
    return [{"start": start, "end": end, "text": text} for start, end, text in rows]


# Sentence-level, as a real transcript arrives: an interviewer turn is only
# recognised as separate from the next one when the answer sits between them, so
# a fixture written in ten coarse blocks would merge all three questions into one.
SABATINA = _talk([
    (0.0, 40.0, "O jornal do SBT News está de volta com o início das sabatinas."),
    (40.0, 44.0, "Candidato, boa noite. A gente começa falando de segurança pública."),
    (44.0, 70.0, "Nós vamos implementar o direito penal do inimigo."),
    (70.0, 100.0, "Facção é organização armada contra o Estado e vai ser tratada assim."),
    (100.0, 130.0, "Quem entra numa facção sabe exatamente o que está fazendo."),
    (130.0, 168.0, "O bandido vai preso, fica um pouquinho na cadeia e termina solto."),
    (168.0, 172.0, "Agora, no lançamento da campanha, os seus apoiadores usaram prendeu matou."),
    (172.0, 200.0, "Diante de um assalto armado, o que que você pode fazer?"),
    (200.0, 240.0, "A vítima não tem alternativa nenhuma naquele instante."),
    (240.0, 270.0, "Ressocializar quem tem pena por crime violento é uma ideia errada."),
    (270.0, 300.0, "O Estado precisa devolver o senso de justiça para quem foi atacado."),
    (300.0, 306.0, "Candidato, eu queria continuar nesse tema da segurança pública."),
    (306.0, 340.0, "A gente tem que ter acordo de cooperação com os Estados Unidos."),
    (340.0, 380.0, "Nós vamos ter que usar inteligência numa boa, com quem quiser cooperar."),
    (380.0, 420.0, "Quem vai destruir o crime no Brasil tem que ser o Brasil."),
])


def test_the_reading_says_where_it_came_from():
    reading = read_source(SABATINA, duration_s=420.0)

    assert reading["origin"] == "furia_entrevista"
    # It matters that this is false: nobody reviewed these boundaries, and the
    # panel has to be able to say so.
    assert reading["reviewed"] is False
    assert reading["unit_count"] >= 2


def test_every_stretch_opens_on_a_question():
    reading = read_source(SABATINA, duration_s=420.0)

    assert all(unit["question"] for unit in reading["units"])
    assert all(unit["duration_s"] >= 25.0 for unit in reading["units"])
    starts = [unit["start_s"] for unit in reading["units"]]
    assert starts == sorted(starts)


def test_frequent_terms_are_never_presented_as_a_title():
    """Furia does not write titles yet, and pretending otherwise would compound.

    The operator would trust a summary the program never produced. Terms travel
    as terms; the title stays empty until a real one exists.
    """
    reading = read_source(SABATINA, duration_s=420.0)

    assert all(unit["title"] == "" for unit in reading["units"])


def test_reviewed_blocks_win_over_anything_derived(tmp_path):
    from modules.acervo_library import store_export

    export = {"items": [{
        "kind": "bloco",
        "id": "b1",
        "title": "Renan promete aplicar o direito penal do inimigo",
        "startS": 51.64, "endS": 168.80, "durationS": 117.16,
        "triggerQuestion": "Como Renan pretende aplicar o direito penal do inimigo?",
        "topics": ["direito penal do inimigo", "facções criminosas"],
        "renanSpeaking": True, "possibleCuts": 1, "riskFlags": ["violencia"],
        "video": {"id": "v1", "youtubeId": "o6yEVC-exk8", "durationS": 420},
        "highlights": [{"sentenceIdx": 34, "startS": 142.4, "endS": 144.2,
                        "text": "Nós vamos implementar o direito penal do inimigo.",
                        "reason": "Afirma a tese central."}],
        "sentences": [],
    }]}
    stored = store_export(export, video_path="Media_o6yEVC-exk8.mp4", data_dir=tmp_path)

    reading = read_source(SABATINA, snapshot_path=stored["path"], duration_s=420.0)

    assert reading["origin"] == "acervo"
    assert reading["reviewed"] is True
    assert reading["units"][0]["title"].startswith("Renan promete")
    assert reading["units"][0]["highlights"][0]["text"].startswith("Nós vamos")
    assert reading["units"][0]["risk_flags"] == ["violencia"]


def test_a_long_question_is_cut_at_a_word():
    reading = read_source(
        _talk([
            (0.0, 30.0, "Candidato, " + "eu queria saber sobre a proposta econômica " * 12),
            (30.0, 120.0, "Vou responder com calma porque o assunto é longo e importante."),
            (120.0, 130.0, "Agora, candidato, falando sobre trabalho, e a CLT?"),
            (130.0, 220.0, "A CLT precisa ser flexibilizada para gerar emprego formal."),
        ]),
        duration_s=220.0,
    )

    for unit in reading["units"]:
        if unit["question"].endswith("…"):
            assert not unit["question"].endswith(" …")
            assert len(unit["question"]) <= 201


def test_nothing_to_read_is_reported_as_such():
    reading = read_source([], duration_s=0.0)

    assert reading["origin"] == "nenhuma"
    assert reading["units"] == []
