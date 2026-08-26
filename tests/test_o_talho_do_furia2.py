"""A tela 4 do Furia 2: o talho — o ajuste fino da borda.

A queixa do editor sobre o ajuste do Furia 1, nas palavras dele: "não sabia o
que eu estava medindo, não sabia onde era o início que eu queria porque o
próprio corte não permitia voltar, e eu sequer sabia se eram segundos". Eram
dois campos de número em segundos absolutos da fonte.

Nada disso se conserta com um rótulo melhor no campo. Som se edita olhando
para o som: aqui o número é consequência do arrasto, e a janela mostra de
propósito um pedaço de FORA do corte, porque para escolher onde entrar é
preciso ouvir a frase anterior.

O teste mais importante deste arquivo é o do ida-e-volta da gravação. O defeito
mais caro do Furia 1 foi um ajuste que respondia 200 e guardava o valor velho,
e ninguém percebeu por duas versões porque a tela nunca conferiu.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"


def carregar_furia2():
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location("furia2_app_talho", RAIZ / "furia2" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def corte(n, inicio, fim, frases=()):
    return {
        "rank": n,
        "start_s": inicio,
        "end_s": fim,
        "duration_s": fim - inicio,
        "origem": "gemini_primary",
        "review_required": False,
        "review_reasons": [],
        "texto": "uma fala",
        "transcricao": [{"t": t, "fim": f, "texto": txt} for t, f, txt in frases],
    }


@pytest.fixture()
def montado(tmp_path, monkeypatch):
    furia2 = carregar_furia2()
    diag = tmp_path / "diagnostics"
    diag.mkdir()
    (tmp_path / "workspace").mkdir()
    monkeypatch.setattr(furia2, "DIAGNOSTICOS", diag)
    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(furia2, "AJUSTES", tmp_path / "ajustes.json")

    folha = {
        "job_id": "abc",
        "fonte": {"arquivo": "debate.mp4", "duracao_s": 1772.1},
        "selecao": {"origem": "gemini", "diagnostico": {}},
        "cortes_renderizados": [
            corte(1, 256.44, 399.58, [
                (256.44, 258.0, "Está certo?"),
                (258.0, 265.0, "O Lula tem que estar nos debates."),
                (395.0, 399.58, "E é sobre isso."),
            ]),
            corte(2, 705.0, 860.0),
        ],
    }
    (diag / "selecao-teste-20260825T084232.json").write_text(
        json.dumps(folha, ensure_ascii=False), encoding="utf-8")
    return furia2, tmp_path


# ── a janela mostra o lado de fora ──────────────────────────────────────────


def test_a_onda_mostra_um_pedaco_de_fora_do_corte(montado):
    """A queixa central era não conseguir VOLTAR. Para escolher onde entrar é
    preciso ouvir a frase anterior — então a janela desenhada é maior que o
    corte, dos dois lados."""
    furia2, _ = montado
    t = furia2.app.test_client().get("/api/talho/trecho", query_string={"n": 1}).get_json()
    assert t["janela"]["inicio"] < t["inicio"], "sumiu a margem antes da entrada"
    assert t["janela"]["fim"] > t["fim"], "sumiu a margem depois da saída"


def test_a_margem_acompanha_o_tamanho_do_corte_mas_tem_teto(montado):
    """Num corte de 30 s, 45 s de margem de cada lado afogariam o corte no
    desenho; num de 3 min, 8 s de margem não deixam ouvir nada."""
    furia2, _ = montado
    assert 8.0 <= furia2.MARGEM_MIN < furia2.MARGEM_MAX <= 60.0
    t = furia2.app.test_client().get("/api/talho/trecho", query_string={"n": 1}).get_json()
    margem = t["inicio"] - t["janela"]["inicio"]
    assert margem == pytest.approx(furia2.MARGEM_MAX), "corte de 143 s devia bater no teto"


def test_a_margem_nao_passa_do_comeco_da_fonte(montado, tmp_path):
    """Um corte que começa aos 5 s não tem 45 s de margem antes dele."""
    furia2, _ = montado
    diag = furia2.DIAGNOSTICOS
    folha = json.loads(next(diag.glob("*.json")).read_text(encoding="utf-8"))
    folha["cortes_renderizados"][0]["start_s"] = 5.0
    folha["cortes_renderizados"][0]["end_s"] = 120.0
    next(diag.glob("*.json")).write_text(json.dumps(folha), encoding="utf-8")

    t = furia2.app.test_client().get("/api/talho/trecho", query_string={"n": 1}).get_json()
    assert t["janela"]["inicio"] == 0.0


def test_o_talho_traz_o_que_a_maquina_propos(montado):
    """Ele precisa poder comparar com a proposta e voltar para ela sem refazer
    a conta de cabeça."""
    furia2, _ = montado
    t = furia2.app.test_client().get("/api/talho/trecho", query_string={"n": 1}).get_json()
    assert t["proposto"] == {"inicio": 256.44, "fim": 399.58}
    assert "[data-voltar]" in JS.read_text(encoding="utf-8")


def test_o_talho_traz_as_frases_com_hora(montado):
    """É com elas que ele vê, ao arrastar, qual frase está ganhando e qual está
    perdendo — que é a pergunta do ofício."""
    furia2, _ = montado
    t = furia2.app.test_client().get("/api/talho/trecho", query_string={"n": 1}).get_json()
    assert len(t["frases"]) == 3
    assert t["frases"][0] == {"t": 256.44, "fim": 258.0, "texto": "Está certo?"}


# ── o ida-e-volta da gravação ───────────────────────────────────────────────


def test_guardar_grava_o_valor_arrastado_e_devolve_o_que_ficou(montado):
    """O defeito mais caro do Furia 1: o ajuste respondia 200 e guardava o
    valor velho. Quem responde aqui é o arquivo, não a intenção."""
    furia2, _ = montado
    cliente = furia2.app.test_client()
    resposta = cliente.post("/api/talho/guardar", json={"n": 1, "inicio": 262.5, "fim": 396.0})
    corpo = resposta.get_json()
    assert corpo["ok"] is True
    assert corpo["inicio"] == 262.5 and corpo["fim"] == 396.0

    # e relendo do zero, sem confiar na resposta anterior:
    de_novo = cliente.get("/api/talho/trecho", query_string={"n": 1}).get_json()
    assert de_novo["inicio"] == 262.5
    assert de_novo["ajustado"] is True
    assert de_novo["proposto"]["inicio"] == 256.44, "a proposta da máquina foi sobrescrita"


def test_a_parede_passa_a_mostrar_a_borda_dele(montado):
    """A parede lendo direto da folha, ignorando o ajuste, é a mesma falha
    calada de sempre — só que em outra tela."""
    furia2, _ = montado
    cliente = furia2.app.test_client()
    cliente.post("/api/talho/guardar", json={"n": 1, "inicio": 262.5, "fim": 396.0})
    c = next(x for x in cliente.get("/api/cortes/lista").get_json()["cortes"] if x["n"] == 1)
    assert c["inicio"] == 262.5
    assert c["duracao"] == pytest.approx(133.5)
    assert c["ajustado"] is True


def test_o_ajuste_de_um_corte_nao_mexe_no_vizinho(montado):
    furia2, _ = montado
    cliente = furia2.app.test_client()
    cliente.post("/api/talho/guardar", json={"n": 1, "inicio": 262.5, "fim": 396.0})
    c2 = next(x for x in cliente.get("/api/cortes/lista").get_json()["cortes"] if x["n"] == 2)
    assert c2["inicio"] == 705.0 and c2["ajustado"] is False


def test_guardar_recusa_um_corte_de_menos_de_um_segundo(montado):
    """Arrastar demais existe. Um corte de zero segundo não é um corte, e o
    programa tem de dizer isso em vez de gravar."""
    furia2, _ = montado
    resposta = furia2.app.test_client().post(
        "/api/talho/guardar", json={"n": 1, "inicio": 300.0, "fim": 300.4})
    assert resposta.status_code == 400
    assert "segundo" in resposta.get_json()["erro"]


@pytest.mark.parametrize("corpo", [
    {"n": 99, "inicio": 1, "fim": 2},
    {"n": 1, "inicio": "abc", "fim": 2},
    {"n": 1},
    {},
])
def test_guardar_recusa_pedido_torto(montado, corpo):
    furia2, _ = montado
    assert furia2.app.test_client().post("/api/talho/guardar", json=corpo).status_code in (400, 404)


def test_o_quadro_do_mural_segue_a_borda_dele():
    """Mexeu no começo, o quadro do mural muda junto. Um mural que continua
    mostrando o quadro velho depois do ajuste é falha calada em imagem."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_cortes_quadro"):]
    assert "_bordas(dados, numero)" in trecho, "o quadro voltou a ler a borda da máquina"


# ── som e imagem são coisas diferentes ──────────────────────────────────────


def test_o_programa_separa_ter_som_de_ter_imagem(montado):
    """Achar a fonte não é o mesmo que ter imagem.

    Quando ele guardou só o áudio de uma entrevista antiga, o talho funciona
    inteiro e o mural não tem quadro nenhum. Pedir onze quadros de um mp3 dava
    onze erros no registro por nada — e linha falsa no registro faz procurar
    defeito onde não tem.
    """
    furia2, _ = montado
    corpo = furia2.app.test_client().get("/api/cortes/lista").get_json()
    assert set(corpo["fonte"]) == {"nome", "segundos", "tem_som", "tem_imagem"}
    assert "tem_imagem" in JS.read_text(encoding="utf-8")


def test_a_fonte_e_procurada_tambem_por_outra_extensao(montado, tmp_path):
    """O talho e o mapa só precisam do SOM. Áudio de meia hora ocupa muito
    menos disco que vídeo de meia hora, e ele guarda só o áudio das antigas."""
    furia2, _ = montado
    (tmp_path / "workspace" / "debate.mp3").write_bytes(b"")
    _, fonte = furia2._folha_da_rodada()
    assert fonte is not None and fonte.suffix == ".mp3"


def test_sem_som_o_talho_diz_em_vez_de_desenhar_nada():
    """Onda vazia sem explicação é o programa parecendo quebrado."""
    codigo = JS.read_text(encoding="utf-8")
    assert "o som da fonte não está nesta máquina" in codigo


# ── o desenho ───────────────────────────────────────────────────────────────


def test_a_onda_e_desenhada_na_densidade_do_monitor():
    """Num notebook com escala de 125% a onda sai borrada — e onda borrada é
    exatamente a que não deixa ver onde a frase começa."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function desenhar()"):]
    assert "devicePixelRatio" in trecho
    assert "setTransform" in trecho


def test_uma_fatia_muda_continua_sendo_uma_linha():
    """Sem piso, o silêncio vira buraco e o desenho parece quebrado no meio de
    uma pausa — e pausa é justamente onde ele quer cortar."""
    codigo = JS.read_text(encoding="utf-8")
    assert "Math.max(0.5, picos[i]" in codigo


def test_a_alca_e_fina_no_desenho_e_larga_no_toque():
    """A linha tem 1 px porque precisa ser precisa; a área de pegar tem 15
    porque o mouse não é."""
    folha = CSS.read_text(encoding="utf-8")
    bloco = folha[folha.find(".f2-alca {"):]
    bloco = bloco[:bloco.find("}")]
    assert "width: 15px" in bloco
    risco = folha[folha.find(".f2-alca::before {"):]
    risco = risco[:risco.find("}")]
    assert "width: 1px" in risco


def test_as_alcas_nunca_se_cruzam():
    codigo = JS.read_text(encoding="utf-8")
    assert "Math.min(t, fim - 1)" in codigo
    assert "Math.max(t, inicio + 1)" in codigo


def test_a_frase_conta_como_dentro_pelo_miolo():
    """Pelo começo, uma frase que o corte pega pela metade apareceria inteira;
    pelo fim, sumiria inteira. O miolo é o que decide se aquela fala vai ao ar
    de forma inteligível."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const centro = (f.t + f.fim) / 2;" in codigo
    assert "centro >= inicio && centro <= fim" in codigo


def test_ouvir_a_borda_pega_os_dois_lados():
    """O gesto que ele repete cem vezes por dia: a frase anterior morrendo e a
    nova nascendo. Tocar só de dentro do corte não responde nada."""
    codigo = JS.read_text(encoding="utf-8")
    assert "ouvir(inicio - 3, inicio + 4)" in codigo
    assert "ouvir(fim - 4, fim + 3)" in codigo


def test_o_som_e_servido_por_faixa():
    """Sem resposta por faixa o navegador baixaria meia hora de mídia para
    ouvir três segundos de borda."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_talho_som"):]
    assert "conditional=True" in trecho


def test_o_talho_abre_sempre_no_corte_escolhido_agora():
    """Uma janela velha aberta de outro corte é a receita da confusão que faz
    gravar o ajuste no corte errado."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("MONTADO.talho ="):]
    assert 'fecharJanela("talho")' in trecho
