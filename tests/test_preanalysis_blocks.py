"""The block panel has to answer for every source, not only for reviewed ones.

The panel read a single global snapshot whose path nobody ever filled, so it
reported "Memória não carregada" on every video the editor ever loaded and the
feature looked dead. These tests pin the fall-through that replaced it, and the
one property that must survive it: a block Furia derived is never dressed up as
a block a person reviewed.
"""

import json

from modules.preanalysis_blocks import blocks_for_source


def _talk(rows):
    return [{"start": start, "end": end, "text": text} for start, end, text in rows]


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


def _acervo_export(tmp_path, youtube_id="o6yEVC-exk8"):
    """One reviewed block filed the way :mod:`acervo_library` files them."""
    export = {
        "schema_version": "campaign-hub-acervo-export-v1",
        "version": "acervo-export-teste",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube", "hook_observations": []}},
        "records": {
            "sources": [{"id": "vid-1", "youtube_id": youtube_id, "title": "Sabatina SBT"}],
            "blocks": [{
                "id": "bloco-1",
                "video_id": "vid-1",
                "title": "Direito penal do inimigo",
                "summary": "O candidato define facção como organização armada contra o Estado.",
                "start_s": 44.0,
                "end_s": 168.0,
                "trigger_question": "A gente começa falando de segurança pública.",
                "renan_speaking": True,
                "trust_tier": "revisado",
            }],
            "highlights": [{
                "id": "bloco-1:3:70",
                "block_id": "bloco-1",
                "start_s": 70.0,
                "end_s": 100.0,
                "text": "Facção é organização armada contra o Estado.",
            }],
            "sentences": [],
        },
    }
    library = tmp_path / "acervo"
    library.mkdir(parents=True, exist_ok=True)
    (library / f"{youtube_id}.json").write_text(json.dumps(export), encoding="utf-8")
    return library


def test_a_source_without_any_export_still_lists_blocks(monkeypatch, tmp_path):
    """The case that made the panel look broken: no export anywhere."""
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))

    payload = blocks_for_source(segments=SABATINA, duration_s=420.0)

    assert payload["available"] is True
    assert payload["blocks"], "a leitura da transcrição tem de render blocos"
    assert payload["origin"] == "furia_entrevista"


def test_a_derived_block_never_claims_to_have_been_reviewed(monkeypatch, tmp_path):
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))

    payload = blocks_for_source(segments=SABATINA, duration_s=420.0)

    assert payload["reviewed"] is False
    for block in payload["blocks"]:
        # No title: a title is something somebody wrote. The card falls back to
        # the position in the source, which is a fact.
        assert block["title"] == ""
        assert block["label"].startswith("Trecho ")
        assert block["summary_is_verbatim"] is True
        assert block["trust_tier"] == "leitura do Furia"


def test_the_summary_of_a_derived_block_is_what_is_actually_said(monkeypatch, tmp_path):
    """Not a paraphrase. The operator has to be able to trust it word for word."""
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))

    payload = blocks_for_source(segments=SABATINA, duration_s=420.0)
    first = payload["blocks"][0]

    spoken = " ".join(
        item["text"] for item in SABATINA
        if first["start"] <= item["start"] < first["end"]
    )
    opening = first["summary"].rstrip("…").strip()
    assert opening and opening in spoken


def test_reviewed_blocks_win_over_the_local_reading(monkeypatch, tmp_path):
    """A person checked those boundaries; no heuristic competes with that."""
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    _acervo_export(tmp_path)

    payload = blocks_for_source(
        video_path="/media/YTDown.com_YouTube_Media_o6yEVC-exk8_001_1080p.mp4",
        segments=SABATINA,
        duration_s=420.0,
    )

    assert payload["origin"] == "acervo"
    assert payload["reviewed"] is True
    assert payload["blocks"][0]["title"] == "Direito penal do inimigo"
    assert payload["blocks"][0]["highlight_count"] == 1


def test_an_export_for_another_video_is_not_used(monkeypatch, tmp_path):
    """The id in the file name is what binds an export to a source."""
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))
    _acervo_export(tmp_path, youtube_id="o6yEVC-exk8")

    payload = blocks_for_source(
        video_path="/media/YTDown.com_YouTube_Media_aB9cD-efGh1_001_1080p.mp4",
        segments=SABATINA,
        duration_s=420.0,
    )

    assert payload["origin"] == "furia_entrevista"
    assert payload["reviewed"] is False


def test_the_search_filters_the_derived_blocks_too(monkeypatch, tmp_path):
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))

    everything = blocks_for_source(segments=SABATINA, duration_s=420.0)
    filtered = blocks_for_source(segments=SABATINA, duration_s=420.0, query="cooperação")

    assert len(filtered["blocks"]) < len(everything["blocks"])
    assert all("cooper" in block["summary"].lower() or "cooper" in block["trigger_question"].lower()
               for block in filtered["blocks"])


def test_without_a_transcript_the_panel_says_what_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path))

    payload = blocks_for_source(segments=[])

    assert payload["available"] is False
    assert payload["blocks"] == []
    assert "transcrição" in payload["message"].lower()
