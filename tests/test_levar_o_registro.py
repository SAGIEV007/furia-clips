"""O registro precisa sair da tela, e a gaveta precisa ser clicável.

O editor, pela terceira vez: "não tem nem console para eu copiar os logs e te
mandar exceto o .bat". As três vezes ele copiou da janela preta do lançador,
porque era o único lugar de onde dava para levar texto embora.

A gaveta existia e mostrava tudo. Mostrar não resolve: selecionar centenas de
linhas com o mouse dentro de uma caixa com rolagem é uma tarefa que ninguém
termina.

E havia um defeito atrás disso, que só apareceu quando o teste de navegador
reclamou que o clique estava sendo interceptado: a barra lateral era fixa, tinha
altura inteira e `z-index: 100`; a gaveta começava em zero com `z-index: 70`.
Os primeiros 248 pixels dela ficavam ATRÁS da barra — e é exatamente ali que
mora o puxador. A olho parecia certo.

Aquela barra lateral não existe mais. O primeiro teste abaixo mudou junto: ele
passou a exigir a ausência da causa em vez da compensação do sintoma.
"""

from pathlib import Path

import pytest

import app as aplicacao

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATE = RAIZ / "templates" / "mesa.html"
ATELIE_CSS = RAIZ / "static" / "css" / "atelie.css"
ATELIE_JS = RAIZ / "static" / "js" / "atelie.js"
MESA_CSS = RAIZ / "static" / "css" / "mesa.css"


def test_nao_existe_barra_lateral_para_engolir_o_puxador():
    """O defeito original não foi corrigido: foi removido junto com a causa.

    Este teste nasceu porque a gaveta começava em zero e os seus primeiros
    248 px ficavam atrás da barra lateral fixa — bem onde mora o puxador. Ele
    exigia `left: var(--at-esquerda)`.

    A barra lateral não existe mais: media a 1366 ela gastava um quinto da
    largura para mostrar um cartão, e a moldura inteira virou uma faixa de
    56 px no topo. Com ela some a única coisa que podia cobrir o puxador, e
    exigir a compensação de um obstáculo que não existe seria proteger o
    passado. O que precisa continuar verdadeiro é o fato, não a fórmula.
    """
    css = MESA_CSS.read_text(encoding="utf-8")
    assert ".sidebar," in css and "display: none !important" in css, (
        "a barra lateral voltou; se voltar, o puxador da gaveta volta a sumir atrás dela"
    )
    atelie = ATELIE_CSS.read_text(encoding="utf-8")
    assert "left: 0; right: 0; bottom: 0;" in atelie, (
        "a gaveta precisa atravessar a tela inteira"
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

    O corte de largura em 1500 px saiu junto com a coluna permanente: ele
    escondia o inspetor abaixo dessa largura, e agora o inspetor SÓ aparece
    quando há algo selecionado. Manter a regra apagaria, num notebook de 1366,
    exatamente o que o editor acabou de clicar para ver.
    """
    assert ".main-content.dock-open .inspetor { display: none; }" in ATELIE_CSS.read_text(encoding="utf-8")
    mesa = MESA_CSS.read_text(encoding="utf-8")
    assert ".inspetor.is-active { display: block; }" in mesa, (
        "o inspetor voltou a ser permanente; ele passava o dia dizendo 'Nada selecionado'"
    )
    assert ".inspetor {\n    display: none;" in mesa, (
        "sem seleção o inspetor tem de estar fora da tela, não vazio dentro dela"
    )


def test_a_previa_nao_toma_um_terco_da_tela():
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert ".player-dock { max-width: 34vw; }" in css
