"""A tela 2 do Furia 2: a fonte.

A janela da fonte responde uma pergunta só — qual vídeo vai para a bancada — e
responde por FOTO, não por nome. Nome de arquivo baixado do YouTube tem cento e
vinte caracteres e trinta deles começam igual; um quadro do vídeo ele reconhece
em meio segundo. É a regra do Cipher (tudo cinza, cor só sob o mouse) fazendo
trabalho de verdade em vez de enfeite.

O teste mais importante deste arquivo é o primeiro. Ele nasceu de um defeito
que só apareceu quando a rota leu o disco de verdade: a lista devolveu 114
cortes já exportados misturados com 5 fontes.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"


def carregar_furia2():
    """O Furia 2 é um programa separado, com o próprio `app.py`.

    Importar pelo nome pegaria o `app` do Furia 1, que é outro programa inteiro
    na mesma pasta-mãe. Por isso o carregamento é pelo caminho.
    """
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location("furia2_app", RAIZ / "furia2" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def furia2():
    return carregar_furia2()


@pytest.fixture()
def cliente(furia2):
    return furia2.app.test_client()


# ── o defeito que o disco de verdade encontrou ──────────────────────────────


def test_a_lista_nao_mistura_corte_pronto_com_fonte(furia2, cliente, tmp_path, monkeypatch):
    """Fonte é ENTRADA. As pastas de saída ficam de fora.

    Na primeira leitura com o disco real a rota varria o workspace inteiro e
    devolvia 114 cortes exportados junto com 5 fontes. Um mural com os cortes
    de ontem dentro não é uma lista de fontes: é um lugar onde ele reconhece o
    próprio trabalho e não acha o vídeo que veio buscar.
    """
    (tmp_path / "uploads").mkdir()
    (tmp_path / "exports").mkdir()
    (tmp_path / "processed").mkdir()
    (tmp_path / "uploads" / "entrevista.mp4").write_bytes(b"x")
    (tmp_path / "exports" / "corte-01.mp4").write_bytes(b"x")
    (tmp_path / "processed" / "corte-02.mp4").write_bytes(b"x")
    (tmp_path / "solta.mp4").write_bytes(b"x")

    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path))
    chaves = {f["chave"] for f in cliente.get("/api/fonte/lista").get_json()["fontes"]}

    assert "uploads/entrevista.mp4" in chaves, "a fonte que estava em uploads sumiu"
    assert "solta.mp4" in chaves, "um vídeo largado na raiz do workspace precisa aparecer"
    assert not any("exports" in c or "processed" in c for c in chaves), (
        f"corte já pronto voltou para a lista de fontes: {sorted(chaves)}"
    )


def test_a_lista_nao_repete_o_mesmo_video(furia2, cliente, tmp_path, monkeypatch):
    """A raiz e as pastas de entrada são varridas em sequência; um arquivo que
    caísse nas duas varreduras apareceria duas vezes no mural."""
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.mp4").write_bytes(b"x")

    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path))
    chaves = [f["chave"] for f in cliente.get("/api/fonte/lista").get_json()["fontes"]]
    assert len(chaves) == len(set(chaves)), f"vídeo repetido no mural: {chaves}"


def test_a_lista_poe_o_mais_recente_na_frente(furia2, cliente, tmp_path, monkeypatch):
    """O vídeo que ele acabou de baixar é quase sempre o que ele quer cortar."""
    import os
    import time

    (tmp_path / "uploads").mkdir()
    velho = tmp_path / "uploads" / "velho.mp4"
    novo = tmp_path / "uploads" / "novo.mp4"
    velho.write_bytes(b"x")
    novo.write_bytes(b"x")
    agora = time.time()
    os.utime(velho, (agora - 90000, agora - 90000))
    os.utime(novo, (agora, agora))

    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path))
    chaves = [f["chave"] for f in cliente.get("/api/fonte/lista").get_json()["fontes"]]
    assert chaves[0].endswith("novo.mp4"), f"a ordem saiu errada: {chaves}"


def test_a_lista_nao_entrega_a_data_de_modificacao(furia2, cliente, tmp_path, monkeypatch):
    """Ela serve só para ordenar aqui dentro. Mandar para a tela um número que
    ninguém mostra é convidar alguém a inventar uso para ele depois."""
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "a.mp4").write_bytes(b"x")
    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path))
    for ficha in cliente.get("/api/fonte/lista").get_json()["fontes"]:
        assert "modificado" not in ficha


# ── o quadro ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("chave", [
    "../../../../etc/passwd",
    "..\\..\\windows\\system32\\config\\sam",
    "/etc/passwd",
    "",
])
def test_o_quadro_nao_serve_arquivo_de_fora_do_workspace(cliente, chave):
    """A chave vem da barra de endereço e é escrita por quem quiser."""
    assert cliente.get("/api/fonte/quadro", query_string={"chave": chave}).status_code == 404


def test_o_quadro_recusa_uma_pasta(cliente):
    """Uma chave vazia resolvia para a própria pasta de trabalho, que existe —
    e daí o ffmpeg era chamado em cima de uma pasta.

    Passava pelo teste de invasão acima pelo motivo errado: dava 404 porque o
    ffmpeg falhava, não porque alguém tinha barrado. Motivo errado é defeito
    esperando o dia em que o motivo mudar.
    """
    assert cliente.get("/api/fonte/quadro", query_string={"chave": "uploads"}).status_code == 404


def test_uma_fonte_de_fora_so_entra_pela_janela_do_windows(furia2):
    """Um arquivo fora da pasta de trabalho só vira fonte depois de ele mesmo
    apontar para ele numa caixa de diálogo do sistema — e aí ele é IMPORTADO.

    Antes existia um registro de caminhos escolhidos, e a fonte de fora ficava
    morando fora. Era isso que fazia "moer" falhar: o motor só aceita vídeo de
    dentro da pasta de trabalho, e escolher na janela do Windows dá o caminho,
    não a permissão. Com a importação, o registro deixou de ter razão de
    existir — e sumiu, em vez de ficar de enfeite.
    """
    assert not hasattr(furia2, "DE_FORA"), (
        "voltou o registro de caminhos de fora; toda fonte agora mora na pasta de trabalho"
    )
    fonte = furia2.__dict__["api_fonte_escolher"]
    assert "choose_path" in fonte.__code__.co_names, (
        "a fonte de fora deixou de passar pela janela do Windows"
    )
    assert "_importar_para_a_pasta" in fonte.__code__.co_names, (
        "a fonte escolhida voltou a ficar do lado de fora"
    )


# ── o link ──────────────────────────────────────────────────────────────────


def test_o_link_e_lido_antes_de_baixar(furia2):
    """Baixar duas horas de entrevista para descobrir que era o vídeo errado é
    meia hora perdida. A rota do link só lê o cabeçalho."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_fonte_ler_link"):]
    trecho = trecho[:trecho.find("\n@app.route", 1)]
    assert "probe_public_url" in trecho
    assert "download" not in trecho.lower(), "a rota de LER começou a baixar"


def test_um_link_ruim_responde_dizendo_o_que_houve(cliente):
    """Erro que não chega na tela é erro que ele passa a tarde procurando."""
    resposta = cliente.post("/api/fonte/ler-link", json={"link": "nao é um link"})
    assert resposta.status_code == 400
    assert resposta.get_json().get("erro"), "o link ruim voltou sem explicação"


# ── a regra da cor, em serviço ──────────────────────────────────────────────


def test_o_mural_fica_cinza_e_so_o_de_baixo_do_mouse_ganha_cor():
    """É a mecânica do Cipher, e aqui ela trabalha: a fonte sob o mouse é a
    única coisa colorida da tela."""
    folha = CSS.read_text(encoding="utf-8")
    assert "filter: grayscale(1)" in folha, "o mural deixou de ficar cinza em repouso"
    assert ".f2-quadro:hover .f2-quadro-tela img" in folha, (
        "a cor deixou de voltar sob o mouse; sem isso o cinza vira só um filtro feio"
    )


def test_a_fonte_montada_aparece_colorida():
    """Na bancada, a fonte escolhida é o único objeto da tela — e é o material
    dele. Material nunca é cinza."""
    folha = CSS.read_text(encoding="utf-8")
    montada = folha[folha.find(".f2-montada-tela img"):]
    assert "grayscale" not in montada[:200], "a fonte na bancada ficou cinza"


def test_o_quadro_e_um_span_com_altura_de_verdade():
    """Os pedaços do quadro são <span>, que nasce em linha, e <span> em linha
    ignora proporção e altura. Sem `display: block` a primeira foto sai no
    tamanho bruto do arquivo e atropela as outras — foi o que apareceu na
    primeira foto desta tela."""
    folha = CSS.read_text(encoding="utf-8")
    bloco = folha[folha.find(".f2-quadro-tela {"):]
    bloco = bloco[:bloco.find("}")]
    assert "display: block" in bloco
    assert "aspect-ratio" in bloco


# ── a janela ────────────────────────────────────────────────────────────────


def test_a_janela_da_fonte_nao_nasce_aberta():
    """Janela que nasce aberta é coluna fixa com outro nome."""
    codigo = JS.read_text(encoding="utf-8")
    assert "MONTADO.fonte = function" in codigo, "a fonte deixou de ser um objeto da doca"
    # Abrir só acontece dentro do que a doca chama, nunca no corpo do arquivo.
    for linha in codigo.splitlines():
        if linha.startswith("    abrirJanela("):
            pytest.fail("alguma janela abre sozinha ao carregar a página")


def test_arrastar_a_janela_nao_pinta_a_tela_de_azul():
    """Programa, não página. Arrastar pelo título não pode ir selecionando o
    nome dos vídeos pelo caminho — e o campo do link continua selecionável."""
    folha = CSS.read_text(encoding="utf-8")
    assert "user-select: none" in folha
    assert "input, textarea" in folha, "a seleção sumiu também de onde ela é necessária"


def test_a_janela_fica_presa_dentro_da_tela():
    """Janela arrastada para fora é janela que ele não consegue mais fechar."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function mover(e)"):]
    trecho = trecho[:trecho.find("}")]
    assert "Math.min" in trecho and "Math.max" in trecho


def test_a_falha_da_rede_vira_recado_na_tela(furia2):
    """Uma resposta de erro nunca pode virar silêncio: quem chama sempre recebe
    algo com `ok` dentro para poder falar na tela."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("async function pedir("):]
    trecho = trecho[:trecho.find("\n    }") + 6]
    assert "resposta.ok" in trecho and "ok: false" in trecho
    assert "f2-ruim" in codigo, "sumiu o vermelho do recado de erro"
