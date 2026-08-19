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


# Um corte de verdade repete o próprio assunto; é disso que sai o trecho em
# destaque. Uma fixture de três frases não repete nada e não tem assunto.
CRYPTO_SRT = """1
00:00:00,000 --> 00:00:04,000
As criptos são uma nova lógica de reserva de valor.

2
00:00:04,000 --> 00:00:09,000
As pessoas sempre darão um jeito de transacionar entre elas.

3
00:00:09,000 --> 00:00:14,000
O Brasil escolheu o caminho arcaico para tratar essa tecnologia.

4
00:00:14,000 --> 00:00:19,000
O caminho arcaico afasta as novas gerações do Brasil.

5
00:00:19,000 --> 00:00:24,000
Quem escolhe o caminho arcaico paga com o próprio futuro.

6
00:00:24,000 --> 00:00:29,000
E o caminho arcaico das criptos é uma escolha do Estado brasileiro.
"""


def _headlines(result, format_id):
    return [item["headline"] for item in result["formats"][format_id]["suggestions"]]


def _sugestoes(result, format_id):
    return result["formats"][format_id]["suggestions"]


CONTEXTO = "Fala do presidenciável Renan Santos sobre a tributação das criptos."


# ── o gancho não é opcional ────────────────────────────────────────────────

def test_toda_headline_sai_com_gancho():
    """As três primeiras headlines geradas foram reprovadas por não terem.

    Antes de qualquer discussão sobre a frase, o editor disse: "não tem uma coisa
    para chamar a atenção como eu fiz no meu". O gancho vem primeiro.
    """
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    sugestoes = _sugestoes(result, FORMAT_SQUARE)
    assert sugestoes
    for item in sugestoes:
        assert item["eyebrow"].strip(), f"headline sem gancho: {item['headline']!r}"
        assert item["eyebrow_alternatives"], "o editor precisa poder trocar o gancho"


# ── a fronteira entre reescrever e citar ───────────────────────────────────

def test_o_resumo_nao_usa_aspas_e_pode_reescrever():
    """Sem aspas não há promessa de literalidade, então parafrasear é legítimo."""
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    resumos = [item for item in _sugestoes(result, FORMAT_SQUARE) if item["mode"] == "resumo"]
    assert resumos, "a forma em terceira pessoa é a que o editor usa"
    for item in resumos:
        assert "“" not in item["headline"] and '"' not in item["headline"]


def test_a_citacao_com_aspas_continua_literal():
    """Com aspas o invariante do NORTE volta a valer, palavra por palavra."""
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    fonte = normalize(CRYPTO_SRT)
    for item in _sugestoes(result, FORMAT_SQUARE):
        if item["mode"] != "citacao":
            continue
        dentro = item["headline"].strip("“”\" ").rstrip("… ")
        assert normalize(dentro) in fonte, (
            f"a citação {dentro!r} não está na fonte; com aspas isso é uma "
            f"citação que ninguém disse"
        )


def test_nenhuma_headline_traz_palavra_que_a_fonte_nao_tem():
    """Parafrasear é dizer com outras palavras o que foi dito.

    Acrescentar o que não foi é outra coisa, e vale para os dois modos.
    """
    from modules.headline_studio import _headline_invents_nothing

    fonte = f"{CRYPTO_SRT} {CONTEXTO}"
    assert _headline_invents_nothing(
        "Renan Santos critica o caminho arcaico das criptos.", fonte
    )
    assert not _headline_invents_nothing(
        "Renan Santos critica o caminho arcaico e defende o bitcoin argentino.", fonte
    )


def test_numero_nunca_e_inventado_mesmo_curto():
    from modules.headline_studio import _headline_invents_nothing

    assert not _headline_invents_nothing(
        "Renan Santos critica os 7 impostos sobre as criptos.", f"{CRYPTO_SRT} {CONTEXTO}"
    )


# ── a frase tem de fazer sentido ───────────────────────────────────────────

def test_a_frase_do_resumo_e_uma_frase():
    """A gramática vem do molde, e o molde não produz frase quebrada.

    Recortar uma janela da própria fala produzia "Existe compra de voto é um
    quanto." — que foi por que essa família passou a ser montada, não recortada.
    """
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    for item in _sugestoes(result, FORMAT_SQUARE):
        if item["mode"] != "resumo":
            continue
        texto = item["headline"]
        assert texto[:1].isupper(), f"headline começa em minúscula: {texto!r}"
        assert texto.endswith((".", "!", "?")), f"headline sem fechamento: {texto!r}"
        assert len(texto.split()) >= 4


def test_o_trecho_destacado_esta_dentro_da_frase():
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    for item in _sugestoes(result, FORMAT_SQUARE):
        if not item["emphasis"]:
            continue
        assert normalize(item["emphasis"]) in normalize(item["headline"])
        assert item["accent"] == "red_on_white"


def test_a_headline_sai_em_caixa_de_frase_e_nao_em_caixa_alta():
    """A caixa alta fica no gancho e no destaque, como na arte aprovada."""
    result = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    resumos = [item for item in _sugestoes(result, FORMAT_SQUARE) if item["mode"] == "resumo"]
    assert resumos
    assert any(item["headline"] != item["headline"].upper() for item in resumos)


# ── atribuição: nunca chutada ──────────────────────────────────────────────

def test_sem_ninguem_respondendo_por_quem_fala_a_forma_em_terceira_pessoa_nao_sai():
    """Ela nomeia a pessoa e afirma o que ela fez; as duas coisas exigem quem."""
    result = generate_artwork_copy(
        "O conselho precisa decidir se aprova a proposta e quais serão as consequências disso.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert all("RENAN" not in item.upper() for item in _headlines(result, FORMAT_VERTICAL))
    assert result["review_flags"]["speaker_unconfirmed"] is True


def test_o_papel_so_entra_com_evidencia():
    """Chamar alguém de presidenciável sem evidência é inventar um fato."""
    from modules.headline_copy import detect_role

    assert detect_role("Fala do presidenciável Renan Santos", "") == "Presidenciável"
    assert detect_role("Renan Santos comentando o mercado", "sobre criptos e bancos") == ""


# ── o caminho de IA ────────────────────────────────────────────────────────

class _ModeloQueInventa:
    def generate(self, prompt, system, emit_progress=None):
        return (
            '{"formats": {"square_alfinetei": [{"eyebrow": "BOMBA!", '
            '"headline": "Renan Santos critica a tributação e cita o dólar argentino."}]}}'
        )


class _ModeloQueReescreve:
    def generate(self, prompt, system, emit_progress=None):
        return (
            '{"formats": {"square_alfinetei": [{"eyebrow": "BOMBA!", '
            '"headline": "O Brasil escolheu o caminho arcaico para as criptos.", '
            '"emphasis": "CAMINHO ARCAICO"}]}}'
        )


def test_a_variacao_que_inventa_uma_palavra_e_descartada():
    base = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    refinado = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE,
        ai_backend=_ModeloQueInventa(),
    )
    assert refinado["generation_source"] == "editorial_local"
    assert _headlines(refinado, FORMAT_SQUARE) == _headlines(base, FORMAT_SQUARE)


def test_a_variacao_que_so_reescreve_e_aceita():
    refinado = generate_artwork_copy(
        CRYPTO_SRT, mini_context=CONTEXTO, preferred_format=FORMAT_SQUARE,
        ai_backend=_ModeloQueReescreve(),
    )
    assert refinado["generation_source"] == "ai_refined"
    principal = _sugestoes(refinado, FORMAT_SQUARE)[0]
    assert "caminho arcaico" in principal["headline"]
    assert principal["emphasis"] == "CAMINHO ARCAICO"
    assert principal["eyebrow"] == "BOMBA!"


# ── silêncio explica o motivo ──────────────────────────────────────────────

def test_quando_nada_sai_a_tela_recebe_o_motivo():
    result = generate_artwork_copy(
        "Boa noite. Obrigado. Prazer todo meu. Muito obrigado mesmo, viu.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert result["formats"][FORMAT_VERTICAL]["suggestions"] == []
    assert result["review_flags"]["no_quote_found"] is True
    assert result["recommendation_reason"].strip()


def test_texto_sem_timestamp_continua_aceito():
    result = generate_artwork_copy(
        "O Estado brasileiro se tornou uma inutilidade que só cobra impostos do trabalhador. "
        "O Estado brasileiro cobra imposto e não entrega nada em troca ao trabalhador.",
        mini_context="Renan Santos, candidato, sobre impostos",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert result["transcript"]["format"] == "plain_text"
    assert _sugestoes(result, FORMAT_VERTICAL)


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
