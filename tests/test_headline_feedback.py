import database


def test_headline_feedback_is_persisted_by_format(monkeypatch, tmp_path):
    test_db = tmp_path / "furia_headlines.sqlite"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()

    database.save_headline_feedback(
        "square_alfinetei",
        "O BRASIL ESCOLHEU O CAMINHO ARCAICO",
        topic="cripto",
        transcript_excerpt="O Brasil escolheu o caminho arcaico.",
    )
    database.save_headline_feedback(
        "vertical_916",
        "CRIPTOS AVANÇAM COM OU SEM O ESTADO",
        action="rejected",
        topic="cripto",
    )

    summary = database.get_headline_feedback_summary()

    assert summary["total"] == 2
    assert summary["selected"] == 1
    assert summary["by_format"] == {"square_alfinetei": 1}
    assert summary["examples"][0]["artwork_text"] == "O BRASIL ESCOLHEU O CAMINHO ARCAICO"
