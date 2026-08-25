"""O registro precisa sair da tela, e a gaveta precisa ser clicável.

O editor, pela terceira vez: "não tem nem console para eu copiar os logs e te
mandar exceto o .bat". As três vezes ele copiou da janela preta do lançador,
porque era o único lugar de onde dava para levar texto embora.

A gaveta existia e mostrava tudo. Mostrar não resolve: selecionar centenas de
linhas com o mouse dentro de uma caixa com rolagem é uma tarefa que ninguém
termina.

E havia um defeito atrás disso, que só apareceu quando o teste de navegador
reclamou que o clique estava sendo interceptado: a barra lateral é fixa, tem
altura inteira e `z-index: 100`; a gaveta começava em zero com `z-index: 70`.
Os primeiros 248 pixels dela ficavam ATRÁS da barra — e é exatamente ali que
mora o puxador. A olho parecia certo.
"""

from pathlib import Path

import pytest

import app as aplicacao

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATE = RAIZ / "templates" / "index.html"
ATELIE_CSS = RAIZ / "static" / "css" / "atelie.css"
ATELIE_JS = RAIZ / "static" / "js" / "atelie.js"


def test_a_gaveta_comeca_depois_da_barra_lateral():
    """Quem é fixo e fica ao lado dela precisa saber onde ela termina."""
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert "--at-esquerda" in css
    assert "left: var(--at-esquerda)" in css, (
        "a gaveta voltou a começar em zero e o puxador some atrás da barra lateral"
    )


def test_os_tres_caminhos_para_levar_o_registro_existem():
    html = TEMPLATE.read_text(encoding="utf-8")
    for botao in ("btnCopiarRegistro", "btnSalvarRegistro", "btnAbrirPastaLogs"):
        assert f'id="{botao}"' in html, f"{botao} sumiu"
    js = ATELIE_JS.read_text(encoding="utf-8")
    for botao in ("btnCopiarRegistro", "btnSalvarRegistro", "btnAbrirPastaLogs"):
        assert botao in js, f"{botao} existe mas não faz nada"


def test_o_texto_copiado_carrega_versao_e_data():
    """Um registro sem versão nem hora não serve para diagnosticar nada."""
    js = ATELIE_JS.read_text(encoding="utf-8")
    trecho = js[js.find("function registro()"):js.find("function registro()") + 700]
    assert "runtimeVersion" in trecho
    assert "toLocaleString" in trecho
    assert "linhas" in trecho


def test_copiar_tem_caminho_alternativo():
    """A área de transferência é negada em alguns navegadores fora de https."""
    js = ATELIE_JS.read_text(encoding="utf-8")
    assert "execCommand" in js, "sem plano B, copiar falha calado em parte dos casos"


def test_abrir_a_pasta_de_logs_responde():
    resposta = aplicacao.app.test_client().post("/api/open-logs")
    corpo = resposta.get_json()
    # Sem ambiente gráfico o comando falha, e aí dizer ONDE fica ainda resolve
    # o problema do editor: ele abre a pasta na mão.
    assert "pasta" in corpo
    assert corpo["pasta"].endswith("logs")
    assert Path(corpo["pasta"]).is_dir()


def test_a_previa_e_o_inspetor_se_revezam():
    """Duas colunas de detalhe à direita comiam dois terços da tela.

    Medido a 1920: com a prévia aberta sobravam menos de 800 px para a coluna do
    meio, e o editor só conseguia ver tudo com zoom de 67%. Prévia e inspetor
    respondem a mesma pergunta — o que está selecionado — então nunca precisam
    estar juntos.
    """
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert ".main-content.dock-open .inspetor { display: none; }" in css
    assert "max-width: 1500px" in css, "o corte de largura para três colunas sumiu"


def test_a_previa_nao_toma_um_terco_da_tela():
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert ".player-dock { max-width: 34vw; }" in css
