"""A identidade tem de estar na tela, não na intenção.

Quatro vezes o editor pediu uma reformulação de desenho. Nas três primeiras eu
troquei arquitetura, cor e espaçamento e mantive o vocabulário visual por baixo,
e ele viu nas três: "você tem apenas reaproveitado o site antigo".

O problema não era falta de esforço — era falta de COMPROMISSO. As referências
que ele mandou (Cipher, Poolsuite) têm em comum escolher um mundo e ir até o
fim. Poolsuite não é "um player com tema retrô", é um objeto de 1985.

Este arquivo existe para que o compromisso não escorra de volta. Cada teste
mede uma decisão que, se for desfeita, devolve o Furia à condição de site
genérico — e nenhum deles mede gosto. Todos medem propriedades que o navegador
calcula.

O que ele NÃO mede, de propósito: se ficou bonito. Isso só a foto responde, e é
por isso que cada rodada desta reforma passou por uma.
"""

import glob
import logging
import os
import re
import threading
import time

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESA_CSS = os.path.join(RAIZ, "static", "css", "mesa.css")
MESA_JS = os.path.join(RAIZ, "static", "js", "mesa.js")


def _so_codigo(caminho):
    """O arquivo sem comentários.

    A primeira versão de `test_o_som_nao_depende_de_arquivo_nenhum` procurava
    ".mp3" no arquivo inteiro e reprovou no meu próprio comentário, que explica
    justamente por que não há .mp3 nenhum. Um teste que lê prosa não está lendo
    o programa.
    """
    fonte = open(caminho, encoding="utf-8").read()
    fonte = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return re.sub(r"^\s*//.*$", "", fonte, flags=re.M)


def _chromium() -> str:
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


# ── o que não pode voltar ──────────────────────────────────────────────────

def test_a_folha_antiga_nao_manda_mais_na_moldura():
    """style.css continua carregado para os widgets fundos, e tudo bem.

    O que não pode voltar é ele decidir a MOLDURA. Se a lousa, a linha ou a
    lâmina voltarem a ser desenhadas lá, a identidade volta a ser um verniz.
    """
    html = open(os.path.join(RAIZ, "templates", "index.html"), encoding="utf-8").read()
    assert "mesa.css" in html, "a folha da mesa saiu do template"
    # E as camadas intermediárias, que existiam só para cobrir a antiga, não
    # podem coexistir com ela: duas camadas de !important brigando foi como o
    # título "Resultados" ficou invisível uma vez.
    assert "sala.css" not in html, "a camada anterior voltou junto com a nova"


def test_a_marca_e_desenhada_e_nao_escrita():
    """Palavra em Inter é palavra de qualquer produto.

    A única fonte que existe offline aqui é a Inter. Um wordmark tipografado
    nela não distingue o Furia de nada — daí o traçado em vetor.
    """
    js = open(MESA_JS, encoding="utf-8").read()
    assert "<svg" in js and "stroke-width" in js, "a marca voltou a ser texto"
    assert js.count("<path") >= 5, "faltam letras no traçado da marca"


def test_o_som_nao_depende_de_arquivo_nenhum():
    """O Furia abre sem internet numa máquina Windows.

    Um .mp3 a mais é um arquivo a mais para faltar. O som é sintetizado, e este
    teste garante que ninguém o troque por assets depois.
    """
    js = _so_codigo(MESA_JS)
    assert "createOscillator" in js
    assert ".mp3" not in js and ".wav" not in js and "new Audio(" not in js, (
        "o som passou a depender de arquivo"
    )


def test_o_som_toca_no_que_o_programa_faz_e_nao_no_que_ele_clica():
    """Um clique sonoro em cada botão vira tortura na terceira hora.

    Os quatro sons são reações do PROGRAMA — corte pronto, operação começou,
    terminou, quebrou. Nenhum deles é "você clicou".
    """
    js = open(MESA_JS, encoding="utf-8").read()
    bloco = js[js.index("const SONS = {"):js.index("window.mesaSom =")]
    assert set(re.findall(r"^\s{8}(\w+):", bloco, re.M)) == {"tique", "armar", "feito", "falha"}

    app = open(os.path.join(RAIZ, "static", "js", "app.js"), encoding="utf-8").read()
    assert 'mesaSom?.("armar")' in app
    assert 'mesaSom?.(completedClips.length ? "feito" : "falha")' in app
    assert "mesaCorteChegou" in app


def test_o_som_pode_ser_desligado_e_a_mesa_lembra():
    js = open(MESA_JS, encoding="utf-8").read()
    assert 'guardar("furia.som"' in js
    assert 'lembrar("furia.som")' in js


def test_a_ignicao_acontece_uma_vez_por_sessao():
    """Ligar um equipamento impressiona na primeira vez. Na décima, atrasa."""
    js = open(MESA_JS, encoding="utf-8").read()
    assert 'sessionStorage.getItem("furia.ligada")' in js, (
        "a ignição passou a rodar em todo carregamento de página"
    )


def test_o_ambar_nunca_entra_em_dado():
    """A regra mais importante do Painel, e ela sobreviveu à troca de identidade.

    Na mesa o âmbar quer dizer uma coisa só: "isto é material do Furia". Se ele
    também pintasse "rendeu bem", as duas leituras se confundiriam na única tela
    onde aparecem juntas.
    """
    atelie = open(os.path.join(RAIZ, "static", "css", "atelie.css"), encoding="utf-8").read()
    bloco = atelie[atelie.index("--viz-acima"):atelie.index("--viz-meio")]
    assert "ffb020" not in bloco.lower() and "--f-ambar" not in bloco, (
        "o âmbar entrou na escala de desempenho e passou a significar duas coisas"
    )


# ── e o que precisa estar aceso ────────────────────────────────────────────

@pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")
def test_a_mesa_esta_desenhada_na_tela():
    """As propriedades que o navegador calcula, não as que eu escrevi.

    Cada uma corresponde a uma decisão do sistema: metal (aresta pegando luz),
    mostrador (monoespaçada tabular), rótulo gravado (entreletra larga) e
    varredura. Juntas são a diferença entre instrumento e formulário — e cada
    uma some sozinha sem ninguém notar.
    """
    playwright_api = pytest.importorskip("playwright.sync_api")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    porta = 5261
    alvo = lambda: aplicacao.app.run(port=porta, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        pagina = navegador.new_page(viewport={"width": 1366, "height": 768})
        erros = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.goto(f"http://127.0.0.1:{porta}/", wait_until="load")
        time.sleep(1.8)
        visto = pagina.evaluate(
            """() => {
                const cs = (sel, prop, pseudo) => {
                    const n = document.querySelector(sel);
                    return n ? getComputedStyle(n, pseudo || null)[prop] : "";
                };
                const painel = document.querySelector('.ambiente.is-active .section')
                            || document.querySelector('.f-lousa');
                return {
                    fundo: cs('body', 'backgroundColor'),
                    varredura: getComputedStyle(document.body, '::after').backgroundImage,
                    metal: painel ? getComputedStyle(painel).boxShadow : '',
                    rotulo: cs('.rail-tab-label', 'letterSpacing'),
                    caixaRotulo: cs('.rail-tab-label', 'textTransform'),
                    mostrador: cs('.runtime-version', 'fontFamily'),
                    tabular: cs('.runtime-version', 'fontVariantNumeric'),
                    marca: !!document.querySelector('.f-marca svg path'),
                    lampada: cs('.rail-tab.is-active', 'backgroundColor', '::after'),
                };
            }"""
        )
        navegador.close()

    assert erros == [], f"erro de JavaScript ao montar a mesa: {erros}"

    # Preto de estúdio, não branco nem cinza de site.
    canais = [int(n) for n in re.findall(r"\d+", visto["fundo"])[:3]]
    assert max(canais) < 30, f"o chão da mesa clareou: {visto['fundo']}"

    assert "repeating-linear-gradient" in visto["varredura"], "a varredura sumiu"
    assert "inset" in visto["metal"], "os painéis perderam a aresta que pega luz"
    assert float(visto["rotulo"].replace("px", "")) > 1.2, (
        f"o rótulo gravado perdeu a entreletra: {visto['rotulo']}"
    )
    assert visto["caixaRotulo"] == "uppercase"
    assert "mono" in visto["mostrador"].lower() or "Consolas" in visto["mostrador"], (
        f"os números saíram do mostrador: {visto['mostrador']}"
    )
    assert "tabular-nums" in visto["tabular"], "os números pararam de alinhar em coluna"
    assert visto["marca"], "a marca desenhada não chegou à tela"
    assert "255, 176, 32" in visto["lampada"], (
        f"a lâmpada da estação ativa apagou: {visto['lampada']}"
    )
