from modules.headline_studio import (
    FORMAT_SQUARE,
    FORMAT_TWEET,
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
        "O Estado precisa decidir se quer acolher ou afastar as criptos do",
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
        preferred_format="auto",
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


def test_learning_can_calibrate_auto_format_only_after_meaningful_history():
    learning = {
        "selected_count": 4,
        "overall_by_format": {"square_alfinetei": 4},
        "topic_by_format": {},
    }
    learned = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos.",
        preferred_format="auto",
        ai_backend=None,
        editorial_learning=learning,
    )
    assert learned["recommended_format"] == FORMAT_SQUARE
    assert learned["learning_applied"]["applied"] is True
    assert learned["learning_applied"]["selected_count"] == 4

    explicit = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
        editorial_learning=learning,
    )
    assert explicit["recommended_format"] == FORMAT_VERTICAL
    assert explicit["learning_applied"]["applied"] is False


def test_endpoint_scopes_headline_learning_to_transcript_topic(monkeypatch):
    import app as app_module

    captured = {}
    def fake_learning(topic=""):
        captured["topic"] = topic
        return {
            "selected_count": 2,
            "overall_by_format": {},
            "topic_by_format": {FORMAT_SQUARE: 2},
        }

    monkeypatch.setattr(app_module, "get_headline_learning_preferences", fake_learning)
    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={"transcript": CRYPTO_SRT, "use_ai": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert captured["topic"] == "cripto"
    assert payload["studio"]["learning_applied"]["applied"] is True
    assert payload["studio"]["recommended_format"] == FORMAT_SQUARE


def test_explicit_headline_format_only_generates_selected_profile():
    result = generate_artwork_copy(
        "O Brasil escolheu o caminho arcaico para tratar as criptos e afastar as novas gerações.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    assert result["generated_format"] == FORMAT_SQUARE
    assert result["formats"][FORMAT_SQUARE]["suggestions"]
    assert result["formats"][FORMAT_VERTICAL]["suggestions"] == []
    assert result["formats"]["fake_tweet"]["suggestions"] == []


def test_headline_studio_endpoint_uses_persisted_clip_transcript(monkeypatch, tmp_path):
    import database
    import app as app_module

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "clip_headline.sqlite"))
    database.init_db()
    project_id = database.create_project("Entrevista", "uploads/entrevista.mp4")
    clip_id = database.save_clip(
        project_id,
        "exports/corte.mp4",
        12.0,
        48.0,
        36.0,
        transcript="O Brasil precisa executar propostas concretas para melhorar a segurança.",
    )

    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={"clip_id": clip_id, "preferred_format": FORMAT_SQUARE, "use_ai": False},
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["studio"]["clip_id"] == clip_id
    assert payload["studio"]["source_interval"] == {"start": 12.0, "end": 48.0}
    assert payload["studio"]["transcript"]["word_count"] > 5


def test_headline_feedback_keeps_clip_identity(monkeypatch, tmp_path):
    import database
    import app as app_module

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "clip_headline_feedback.sqlite"))
    database.init_db()
    project_id = database.create_project("Entrevista", "uploads/entrevista.mp4")
    clip_id = database.save_clip(
        project_id,
        "exports/corte.mp4",
        12.0,
        48.0,
        36.0,
        transcript="A proposta precisa ter contexto e conclusão.",
    )
    clip = database.get_clip(clip_id)

    response = app_module.app.test_client().post(
        "/api/headline-studio/feedback",
        json={
            "clip_id": clip_id,
            "format_id": FORMAT_SQUARE,
            "artwork_text": "A PROPOSTA PRECISA TER CONCLUSÃO",
            "action": "selected",
            "transcript_excerpt": clip["transcript"],
        },
    )

    assert response.status_code == 200
    conn = database.get_db()
    row = conn.execute(
        "SELECT clip_id, editorial_key, source FROM headline_feedback ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row["clip_id"] == clip_id
    assert row["editorial_key"] == clip["editorial_key"]
    assert row["source"] == "clip_headline_studio"


def test_headline_studio_rejects_unknown_clip_id():
    import app as app_module

    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={"clip_id": 999999, "use_ai": False},
    )

    assert response.status_code == 404
    assert "corte" in response.get_json()["error"].lower()


EMENDAS_TRANSCRIPT = """Hoje o deputado precisa de cada vez mais emendas. O Flávio Dino combate penduricalhos, mas também está perseguindo jornalista. As emendas devem ser vinculadas a políticas públicas que aumentam indicadores, como o fornecimento de água potável, em vez de praças mal feitas."""


def test_headline_topic_follows_transcript_evidence_instead_of_generic_security_label():
    result = generate_artwork_copy(
        EMENDAS_TRANSCRIPT,
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )

    assert result["topic"] == "emendas"
    assert any(item.startswith("emenda") for item in result["topic_evidence"])
    headlines = [item["headline"] for item in result["formats"][FORMAT_VERTICAL]["suggestions"]]
    assert any("EMEND" in headline or "FLÁVIO DINO" in headline for headline in headlines)
    assert all("SEGURANÇA" not in headline for headline in headlines)


def test_generic_headlines_do_not_attribute_speaker_without_explicit_context():
    result = generate_artwork_copy(
        "O conselho precisa decidir se aprova a proposta e quais serão as consequências.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )

    headlines = [item["headline"] for item in result["formats"][FORMAT_VERTICAL]["suggestions"]]
    assert headlines
    assert all("RENAN" not in headline for headline in headlines)



def test_headline_studio_uses_aggregate_approved_clip_format_prior_only_when_eligible():
    result = generate_artwork_copy(
        CRYPTO_SRT,
        preferred_format="",
        ai_backend=None,
        editorial_learning={
            "approved_clip_prior": {
                "eligible": True,
                "approved_count": 18,
                "approved_by_format": {FORMAT_SQUARE: 12, FORMAT_VERTICAL: 6},
                "influence_scope": "aggregate-only; bounded prior, never a gate or fine-tune",
            }
        },
    )
    assert result["recommended_format"] == FORMAT_SQUARE
    assert result["learning_applied"]["applied"] is True
    assert result["learning_applied"]["selected_count"] == 12
    assert "aggregate-only" in result["analysis"]["approved_clip_prior"]["influence_scope"]
    assert result["formats"][FORMAT_SQUARE]["suggestions"]
    assert "approved_by_format" not in str(result["formats"][FORMAT_SQUARE]["suggestions"])


FISCAL_CUT_TRANSCRIPT = """e o que que nós temos? um país que é pobre mas que cobra imposto de país rico pra você poder mexer nisso sem estourar a trajetória da relação em dívida PIB que hoje tá indo estourar cê vai ter que mexer na despesa e aí eu tô avisando pra todo mundo e eu sou o único pré candidato que não está mentindo sobre esse assunto eu tô falando mexer em mais de duzentos bilhões por ano na parte de despesa então vai ter que mexer nas indexações a subida do salário mínimo pra aposentadoria bpc outros benefícios tô falando das vinculações de educação e saúde"""


def test_plain_text_without_terminal_punctuation_is_not_always_incomplete():
    result = generate_artwork_copy(
        "O Estado precisa decidir se quer acolher ou afastar as criptos do Brasil",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )

    assert result["review_flags"]["transcript_ends_incomplete"] is False


def test_fiscal_caption_generates_grounded_headlines_without_crypto_drift():
    result = generate_artwork_copy(
        FISCAL_CUT_TRANSCRIPT,
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )

    suggestions = result["formats"][FORMAT_SQUARE]["suggestions"]
    headlines = [item["headline"] for item in suggestions]
    joined = " ".join(headlines)

    assert result["topic"] == "economia"
    assert "200 BILHÕES" in joined or "IMPOSTO" in joined or "DESPESAS" in joined
    assert "CRIPTO" not in joined
    assert "PRÓPRIO FUTURO" not in joined
    assert result["analysis"]["headline_basis"]["grounded_claims"]
    assert result["review_flags"]["transcript_ends_incomplete"] is False


def test_fiscal_caption_fake_tweet_uses_the_cut_claim_not_a_generic_topic_phrase():
    result = generate_artwork_copy(
        FISCAL_CUT_TRANSCRIPT,
        preferred_format=FORMAT_TWEET,
        ai_backend=None,
    )

    post_text = result["formats"][FORMAT_TWEET]["suggestions"][0]["post_text"]
    assert "200 bilhões" in post_text or "imposto" in post_text or "despesas" in post_text
    assert "olhar para o futuro" not in post_text
