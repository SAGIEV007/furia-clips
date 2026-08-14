from modules.headline_studio import (
    FORMAT_SQUARE,
    FORMAT_VERTICAL,
    generate_artwork_copy,
)


CRYPTO_SRT = """1
00:00:00,000 --> 00:00:03,000
As criptos são uma nova lógica.

2
00:00:03,000 --> 00:00:07,000
As pessoas sempre darão um jeito de transacionar.

3
00:00:07,000 --> 00:00:11,000
O Brasil escolheu o caminho arcaico.
"""


def test_square_artwork_copy_is_short_and_uses_top_callout():
    result = generate_artwork_copy(
        CRYPTO_SRT,
        mini_context="Crítica à tributação de criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )

    assert result["recommended_format"] == FORMAT_SQUARE
    suggestion = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert suggestion["eyebrow"] == "ARCAICO"
    assert len(suggestion["headline"]) <= 64
    assert len(suggestion["headline_lines"]) <= 3
    assert "CAMINHO ARCAICO" in suggestion["headline"]
    assert result["transcript"]["timestamped"] is True


def test_plain_finished_cut_text_is_accepted_without_timestamps():
    result = generate_artwork_copy(
        "O Estado precisa decidir se quer acolher ou afastar as criptos do Brasil",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )

    assert result["recommended_format"] == FORMAT_VERTICAL
    assert result["transcript"]["format"] == "plain_text"
    assert result["formats"][FORMAT_VERTICAL]["suggestions"]
    assert result["review_flags"]["transcript_ends_incomplete"] is True


def test_headline_studio_endpoint_returns_artwork_copy_without_ai(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "get_all_settings", lambda: {"ai_backend": "gemini"})
    client = app_module.app.test_client()
    response = client.post(
        "/api/headline-studio/analyze",
        json={
            "transcript": CRYPTO_SRT,
            "mini_context": "Corte 1:1 sobre criptoativos.",
            "preferred_format": FORMAT_SQUARE,
            "use_ai": False,
        },
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["studio"]["recommended_format"] == FORMAT_SQUARE
    assert payload["studio"]["formats"][FORMAT_SQUARE]["suggestions"]


def test_headline_studio_endpoint_requires_transcript():
    import app as app_module

    client = app_module.app.test_client()
    response = client.post("/api/headline-studio/analyze", json={"transcript": ""})

    assert response.status_code == 400
    assert "transcrição" in response.get_json()["error"].lower()


def test_headline_feedback_endpoint_saves_choice(monkeypatch):
    import app as app_module

    received = {}
    monkeypatch.setattr(app_module, "save_headline_feedback", lambda *args, **kwargs: received.update({"args": args, "kwargs": kwargs}))
    monkeypatch.setattr(
        app_module,
        "get_headline_feedback_summary",
        lambda: {"total": 1, "selected": 1, "by_format": {"square_alfinetei": 1}, "examples": []},
    )
    client = app_module.app.test_client()
    response = client.post(
        "/api/headline-studio/feedback",
        json={
            "format_id": "square_alfinetei",
            "artwork_text": "O BRASIL ESCOLHEU O CAMINHO ARCAICO",
            "action": "selected",
            "topic": "cripto",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["learning"]["selected"] == 1
    assert received["args"][:2] == ("square_alfinetei", "O BRASIL ESCOLHEU O CAMINHO ARCAICO")


def test_square_headline_keeps_claim_and_exposes_layout_budget():
    result = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos e afastar as novas gerações.",
        mini_context="Comentário de Renan sobre criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )

    suggestion = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert "CAMINHO ARCAICO" in suggestion["headline"]
    assert len(suggestion["headline_lines"]) <= 3
    assert suggestion["word_count"] == len(suggestion["headline"].split())
    assert "até 3 linhas" in suggestion["layout_hint"]


def test_vertical_headline_uses_a_tighter_line_budget_than_square():
    result = generate_artwork_copy(
        "O Estado precisa decidir se vai acolher ou afastar as criptos do Brasil.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )

    vertical = result["formats"][FORMAT_VERTICAL]["suggestions"][0]
    square = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert "cerca de 19 caracteres" in vertical["layout_hint"]
    assert "cerca de 23 caracteres" in square["layout_hint"]


def test_square_uses_short_speaker_attribution_only_when_editor_identifies_renan():
    result = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos.",
        mini_context="Fala de Renan Santos sobre criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    headline = result["formats"][FORMAT_SQUARE]["suggestions"][0]["headline"]
    assert headline.startswith("RENAN:")
    assert len(headline) <= 64

    generic = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos.",
        mini_context="Comentário sobre criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    generic_headline = generic["formats"][FORMAT_SQUARE]["suggestions"][0]["headline"]
    assert not generic_headline.startswith("RENAN:")
