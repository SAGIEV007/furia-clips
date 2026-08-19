"""A headline é estampa, atribuição e uma citação que a pessoa disse.

O módulo antigo não gerava headline: era uma cadeia de condições fixas tirada de
um vídeo sobre criptomoedas, e para qualquer fonte nova caía num genérico. Num
corte sobre cotas e ensino básico ele respondeu "O BRASIL QUER TRIBUTAR O PRÓPRIO
FUTURO?" — porque o trecho continha a palavra "imposto" — e nada daquilo tinha
sido dito.

O invariante que substitui aquilo é um só e é duro: **a citação é literal.** Estes
testes existem para que ele não possa ser afrouxado sem alguém perceber.
"""

import pytest

from modules.headline_studio import (
    FORMAT_SQUARE,
    FORMAT_VERTICAL,
    generate_artwork_copy,
)
from modules.political_profile import normalize


CRYPTO_SRT = """1
00:00:00,000 --> 00:00:04,000
As criptos são uma nova lógica de reserva de valor.

2
00:00:04,000 --> 00:00:09,000
As pessoas sempre darão um jeito de transacionar entre elas.

3
00:00:09,000 --> 00:00:14,000
O Brasil escolheu o caminho arcaico para tratar essa tecnologia.
"""


def _headlines(result, format_id):
    return [item["headline"] for item in result["formats"][format_id]["suggestions"]]


def _quotes(result, format_id):
    return [item["quote"] for item in result["formats"][format_id]["suggestions"]]


# ── o invariante ───────────────────────────────────────────────────────────

def test_toda_citacao_aparece_palavra_por_palavra_na_transcricao():
    result = generate_artwork_copy(
        CRYPTO_SRT,
        mini_context="Fala de Renan Santos sobre criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    fonte = normalize(result["transcript"]["excerpt"] + " " + CRYPTO_SRT)
    citacoes = _quotes(result, FORMAT_SQUARE)
    assert citacoes, "o gerador precisa devolver ao menos uma citação"
    for citacao in citacoes:
        alvo = normalize(citacao["text"].rstrip("… ."))
        assert alvo in fonte, (
            f"a citação {citacao['text']!r} não está na transcrição; "
            f"uma citação reescrita é uma citação que ninguém disse"
        )


def test_a_headline_carrega_a_frase_e_nao_um_molde():
    result = generate_artwork_copy(
        CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    headlines = _headlines(result, FORMAT_SQUARE)
    assert headlines
    assert all("A VERDADE INCÔMODA SOBRE" not in item for item in headlines), (
        "o genérico do módulo antigo voltou"
    )
    assert any("caminho arcaico" in item for item in headlines)


def test_uma_frase_longa_e_cortada_numa_fronteira_de_oracao_e_o_corte_e_declarado():
    longa = (
        "A modalidade de emenda como nós temos hoje, que é a emenda roubalheira "
        "vinda de um acordo velho entre o Congresso e o governo de plantão, ela "
        "não pode de jeito nenhum ser a modalidade com a qual eu vou trabalhar."
    )
    result = generate_artwork_copy(longa, preferred_format=FORMAT_VERTICAL, ai_backend=None)
    citacoes = _quotes(result, FORMAT_VERTICAL)
    assert citacoes
    citacao = citacoes[0]
    if not citacao["verbatim"]:
        assert citacao["text"].endswith("…"), "o corte tem de ser visível na própria citação"
        assert normalize(citacao["text"].rstrip("… ")) in normalize(longa)


# ── atribuição: nunca chutada ──────────────────────────────────────────────

def test_sem_ninguem_respondendo_por_quem_fala_a_headline_sai_sem_nome():
    result = generate_artwork_copy(
        "O conselho precisa decidir se aprova a proposta e quais serão as consequências disso.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    headlines = _headlines(result, FORMAT_VERTICAL)
    assert headlines
    assert all("RENAN" not in item for item in headlines)
    assert result["review_flags"]["speaker_unconfirmed"] is True


def test_o_editor_dizendo_de_quem_e_a_fonte_atribui_o_nome_sem_verbo_forte():
    """O editor responde por "quem"; só o áudio responde por "com que força"."""
    result = generate_artwork_copy(
        CRYPTO_SRT,
        mini_context="Fala de Renan Santos sobre criptoativos.",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    sugestao = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert sugestao["attribution"].startswith("RENAN"), sugestao["attribution"]
    assert sugestao["attribution"].endswith(":")
    assert sugestao["attribution_level"] == "editor"
    assert not any(
        verbo in sugestao["attribution"] for verbo in ("DETONA", "CRAVA", "PROMETE", "DIZ")
    ), "verbo de força sem o áudio ter confirmado o locutor"


def test_o_audio_confirmando_o_locutor_autoriza_o_verbo_da_atribuicao():
    result = generate_artwork_copy(
        CRYPTO_SRT,
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
        speaker_name="Renan Santos",
        speaker_level="audio",
    )
    sugestao = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert sugestao["attribution_level"] == "audio"
    assert sugestao["attribution"].startswith("RENAN SANTOS ")
    assert sugestao["attribution"].rstrip(":").split()[-1] in {"DETONA", "CRAVA", "PROMETE", "DIZ"}


# ── o que não vira citação ─────────────────────────────────────────────────

def test_cortesia_do_programa_nao_vira_citacao():
    result = generate_artwork_copy(
        "Seja muito bem-vindo ao nosso programa de hoje. Prazer todo meu, obrigado pelo convite. "
        "O Estado brasileiro se tornou uma inutilidade que só cobra impostos do trabalhador.",
        mini_context="Renan Santos",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    headlines = _headlines(result, FORMAT_VERTICAL)
    assert headlines
    assert all("bem-vindo" not in item and "Prazer" not in item for item in headlines)
    assert any("inutilidade" in item for item in headlines)


def test_frase_que_continua_a_anterior_nao_vira_citacao():
    result = generate_artwork_copy(
        "O Brasil precisa enfrentar o crime organizado com seriedade e método. "
        "E aí a gente vai ver o resultado disso lá na frente, sem pressa nenhuma.",
        mini_context="Renan Santos",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    for citacao in _quotes(result, FORMAT_VERTICAL):
        assert not citacao["text"].startswith("E aí"), (
            "uma citação que abre continuando outra frase tem o mesmo defeito de "
            "um corte que abre ali"
        )


def test_quando_nenhuma_frase_se_sustenta_o_silencio_explica_o_motivo():
    result = generate_artwork_copy(
        "Boa noite. Obrigado. Prazer todo meu. Muito obrigado mesmo, viu.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert result["formats"][FORMAT_VERTICAL]["suggestions"] == []
    assert result["review_flags"]["no_quote_found"] is True
    assert "sustenta" in result["recommendation_reason"]


def test_a_citacao_guarda_o_instante_em_que_foi_dita():
    """É o timestamp que deixa conferir no áudio, e o áudio é a fonte da verdade."""
    result = generate_artwork_copy(CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=None)
    citacao = _quotes(result, FORMAT_SQUARE)[0]
    assert citacao["start_s"] is not None
    assert citacao["end_s"] is not None and citacao["end_s"] > citacao["start_s"]


# ── o caminho de IA não pode reescrever ────────────────────────────────────

class _ModeloQueParafraseia:
    def generate(self, prompt, system, emit_progress=None):
        return (
            '{"formats": {"square_alfinetei": [{"eyebrow": "ABSURDO!", '
            '"headline": "RENAN: \\u201cO Brasil optou pela via ultrapassada de tratar a tecnologia\\u201d"}]}}'
        )


class _ModeloQueCita:
    def generate(self, prompt, system, emit_progress=None):
        return (
            '{"formats": {"square_alfinetei": [{"eyebrow": "OLHA ISSO", '
            '"headline": "RENAN: \\u201cO Brasil escolheu o caminho arcaico para tratar essa tecnologia.\\u201d"}]}}'
        )


def test_a_variacao_do_modelo_que_reescreve_a_citacao_e_descartada():
    base = generate_artwork_copy(CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=None)
    refinado = generate_artwork_copy(
        CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=_ModeloQueParafraseia()
    )
    assert refinado["generation_source"] == "literal_quote", (
        "a paráfrase do modelo foi aceita; a citação deixou de ser literal"
    )
    assert _headlines(refinado, FORMAT_SQUARE) == _headlines(base, FORMAT_SQUARE)


def test_a_variacao_do_modelo_que_cita_ao_pe_da_letra_e_aceita():
    refinado = generate_artwork_copy(
        CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=_ModeloQueCita()
    )
    assert refinado["generation_source"] == "ai_refined"
    assert any("caminho arcaico" in item for item in _headlines(refinado, FORMAT_SQUARE))


# ── o formato que saiu ─────────────────────────────────────────────────────

def test_o_formato_fake_tweet_nao_existe_mais():
    from modules.headline_studio import FORMAT_IDS, FORMAT_PROFILES

    assert "fake_tweet" not in FORMAT_IDS
    assert "fake_tweet" not in FORMAT_PROFILES
    result = generate_artwork_copy(CRYPTO_SRT, ai_backend=None)
    assert "fake_tweet" not in result["formats"]


def test_a_rota_recusa_o_formato_descartado():
    import app as app_module

    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={"transcript": CRYPTO_SRT, "preferred_format": "fake_tweet", "use_ai": False},
    )
    assert response.status_code == 400


# ── contrato de layout e de formato, que a interface lê ────────────────────

def test_o_formato_pedido_e_o_unico_gerado():
    result = generate_artwork_copy(CRYPTO_SRT, preferred_format=FORMAT_SQUARE, ai_backend=None)
    assert result["generated_format"] == FORMAT_SQUARE
    assert result["formats"][FORMAT_SQUARE]["suggestions"]
    assert result["formats"][FORMAT_VERTICAL]["suggestions"] == []


def test_o_vertical_tem_orcamento_de_linha_mais_apertado_que_o_quadrado():
    result = generate_artwork_copy(CRYPTO_SRT, preferred_format="auto", ai_backend=None)
    vertical = result["formats"][FORMAT_VERTICAL]["suggestions"][0]
    square = result["formats"][FORMAT_SQUARE]["suggestions"][0]
    assert "cerca de 19 caracteres" in vertical["layout_hint"]
    assert "cerca de 23 caracteres" in square["layout_hint"]
    assert len(vertical["headline_lines"]) <= 3


def test_texto_sem_timestamp_continua_aceito():
    result = generate_artwork_copy(
        "O Estado brasileiro se tornou uma inutilidade que só cobra impostos do trabalhador.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert result["transcript"]["format"] == "plain_text"
    assert result["formats"][FORMAT_VERTICAL]["suggestions"]
    assert _quotes(result, FORMAT_VERTICAL)[0]["start_s"] is None


def test_o_tema_continua_saindo_da_evidencia_do_texto():
    result = generate_artwork_copy(
        "As emendas parlamentares devem ser vinculadas a políticas públicas com indicadores "
        "de desempenho, e não ao aumento da receita do orçamento de cada deputado.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert result["topic"] == "emendas"
    assert any(item.startswith("emenda") for item in result["topic_evidence"])


def test_o_aprendizado_calibra_o_formato_so_com_historico_suficiente():
    learning = {"selected_count": 4, "overall_by_format": {FORMAT_SQUARE: 4}, "topic_by_format": {}}
    aprendido = generate_artwork_copy(
        CRYPTO_SRT, preferred_format="auto", ai_backend=None, editorial_learning=learning
    )
    assert aprendido["recommended_format"] == FORMAT_SQUARE
    assert aprendido["learning_applied"]["applied"] is True

    explicito = generate_artwork_copy(
        CRYPTO_SRT, preferred_format=FORMAT_VERTICAL, ai_backend=None, editorial_learning=learning
    )
    assert explicito["recommended_format"] == FORMAT_VERTICAL
    assert explicito["learning_applied"]["applied"] is False


# ── rotas ──────────────────────────────────────────────────────────────────

def test_a_rota_devolve_texto_de_arte_sem_ia(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "get_all_settings", lambda: {"ai_backend": "gemini"})
    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={
            "transcript": CRYPTO_SRT,
            "mini_context": "Corte 1:1 sobre criptoativos com Renan Santos.",
            "preferred_format": FORMAT_SQUARE,
            "use_ai": False,
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["studio"]["formats"][FORMAT_SQUARE]["suggestions"]


def test_a_rota_exige_transcricao():
    import app as app_module

    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze", json={"transcript": ""}
    )
    assert response.status_code == 400
    assert "transcrição" in response.get_json()["error"].lower()


def test_a_rota_recusa_corte_inexistente():
    import app as app_module

    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze", json={"clip_id": 999999, "use_ai": False}
    )
    assert response.status_code == 404
    assert "corte" in response.get_json()["error"].lower()


def test_a_rota_usa_a_transcricao_guardada_do_corte(monkeypatch, tmp_path):
    import database
    import app as app_module

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "clip_headline.sqlite"))
    database.init_db()
    project_id = database.create_project("Entrevista", "uploads/entrevista.mp4")
    clip_id = database.save_clip(
        project_id, "exports/corte.mp4", 12.0, 48.0, 36.0,
        transcript="O Brasil precisa executar propostas concretas para melhorar a segurança pública.",
    )
    response = app_module.app.test_client().post(
        "/api/headline-studio/analyze",
        json={"clip_id": clip_id, "preferred_format": FORMAT_SQUARE, "use_ai": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["studio"]["clip_id"] == clip_id
    assert payload["studio"]["source_interval"] == {"start": 12.0, "end": 48.0}


def test_o_feedback_guarda_a_escolha(monkeypatch):
    import app as app_module

    recebido = {}
    monkeypatch.setattr(
        app_module, "save_headline_feedback",
        lambda *args, **kwargs: recebido.update({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(
        app_module, "get_headline_feedback_summary",
        lambda: {"total": 1, "selected": 1, "by_format": {FORMAT_SQUARE: 1}, "examples": []},
    )
    response = app_module.app.test_client().post(
        "/api/headline-studio/feedback",
        json={
            "format_id": FORMAT_SQUARE,
            "artwork_text": 'RENAN: "O Brasil escolheu o caminho arcaico"',
            "action": "selected",
            "topic": "cripto",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["learning"]["selected"] == 1
    assert recebido["args"][0] == FORMAT_SQUARE


def test_o_feedback_mantem_a_identidade_do_corte(monkeypatch, tmp_path):
    import database
    import app as app_module

    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "clip_headline_feedback.sqlite"))
    database.init_db()
    project_id = database.create_project("Entrevista", "uploads/entrevista.mp4")
    clip_id = database.save_clip(
        project_id, "exports/corte.mp4", 12.0, 48.0, 36.0,
        transcript="A proposta precisa ter contexto e conclusão.",
    )
    clip = database.get_clip(clip_id)
    response = app_module.app.test_client().post(
        "/api/headline-studio/feedback",
        json={
            "clip_id": clip_id,
            "format_id": FORMAT_SQUARE,
            "artwork_text": 'RENAN: "A proposta precisa ter contexto e conclusão."',
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
