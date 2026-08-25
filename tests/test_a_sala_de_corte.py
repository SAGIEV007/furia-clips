"""A moldura tinha de encolher, e o mapa tinha de dizer a verdade.

"a experiência é HORRÍVEL", "só ficou totalmente visível com zoom de 67%", "até
o menu da esquerda é IDÊNTICO". Três reclamações, uma causa só, e ela não era
cor nem canto arredondado — era ARQUITETURA.

Medido nas fotos da tela dele, antes: quatro faixas de moldura antes de qualquer
conteúdo (barra lateral com um cartão e o resto vazio, cabeçalho de marketing,
trilha decorativa de quatro etapas, barra de ambientes), mais um inspetor
permanente à direita dizendo "Nada selecionado". Numa tela de 1366×768 isso
comia um quinto da largura e um terço da altura.

Este arquivo mede as duas coisas que a reforma promete, no navegador, na tela
dele — porque "parece melhor" não é medida:

1. Quanto da tela sobrou para o trabalho.
2. Se o mapa da fonte conta a história certa sobre a rodada real dele.

O mapa é a peça nova. Ele responde, sem abrir arquivo nenhum, a pergunta que o
editor repete toda rodada: "estou perdendo cortes?". Os números da fixture são
os da corrida PENÉLOPE — 29min32 de fonte, 11 cortes entregues, 21 candidatos
derrubados pela peneira, 12 deles inteiros dentro de um corte que ele recebeu.
"""

import glob
import json
import logging
import os
import threading
import time

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _chromium() -> str:
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


playwright_api = pytest.importorskip("playwright.sync_api", reason="playwright ausente")
pytestmark = pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")

PORTA = 5231
FONTE_S = 1772.1

# Os onze cortes da PENÉLOPE, nas posições reais em que saíram.
CORTES = [
    {"start": 472.0, "end": 591.4}, {"start": 705.0, "end": 859.9},
    {"start": 256.6, "end": 399.6}, {"start": 371.5, "end": 471.5},
    {"start": 87.7, "end": 174.6}, {"start": 940.0, "end": 999.0},
    {"start": 1305.0, "end": 1422.0}, {"start": 1180.0, "end": 1238.0},
    {"start": 1505.0, "end": 1618.0}, {"start": 1445.0, "end": 1558.0},
    {"start": 1725.0, "end": 1756.0},
]
CORTES = [
    dict(c, clip_id=f"c{i}", duration=c["end"] - c["start"], rank=i + 1,
         viral_score=70 - i, source="gemini", source_duration=FONTE_S,
         text=f"Trecho número {i + 1} da fonte.")
    for i, c in enumerate(CORTES)
]

# Dois descartes de tipos opostos: um engolido inteiro por um corte entregue
# (conteúdo que ele já tem) e um que só encostava na borda (perda de verdade).
DESCARTADOS = [
    {"motivo": "overlap", "inicio": 480.0, "fim": 520.0, "duracao": 40.0,
     "vencedor_inicio": 472.0, "vencedor_fim": 591.4, "vencedor_duracao": 119.4,
     "dentro_do_vencedor": True, "trecho": "Um pedaço da mesma resposta."},
    {"motivo": "overlap", "inicio": 1194.0, "fim": 1361.0, "duracao": 167.0,
     "vencedor_inicio": 1305.0, "vencedor_fim": 1422.0, "vencedor_duracao": 117.0,
     "dentro_do_vencedor": False, "trecho": "Outra fala inteira, que morreu na borda."},
]


@pytest.fixture(scope="module")
def pagina_do_editor():
    """A tela dele: 1366 × 768, com a rodada real carregada."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    alvo = lambda: aplicacao.app.run(port=PORTA, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        pagina = navegador.new_page(viewport={"width": 1366, "height": 768})
        erros = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.goto(f"http://127.0.0.1:{PORTA}/", wait_until="load")
        time.sleep(1.2)
        pagina.evaluate(
            """([cortes, descartados, duracao]) => {
                state.clips = cortes;
                state.sourceDuration = duracao;
                state.diagnostics = { descartados_por_sobreposicao: descartados };
                document.querySelector('.rail-tab[data-ambiente="auditoria"]').click();
                renderResultsGrid();
            }""",
            [CORTES, DESCARTADOS, FONTE_S],
        )
        time.sleep(0.8)
        yield pagina, erros
        navegador.close()


def test_a_tela_nao_quebra(pagina_do_editor):
    _, erros = pagina_do_editor
    assert erros == [], f"erro de JavaScript ao montar a sala: {erros}"


def test_a_moldura_cabe_numa_faixa(pagina_do_editor):
    """Quatro faixas viraram uma.

    O número é o que importa: quantos pixels de altura o editor gasta antes de
    ver a primeira coisa útil. Eram cerca de 250; a barra do topo tem 56.
    """
    pagina, _ = pagina_do_editor
    topo = pagina.locator(".topo").bounding_box()
    assert topo["height"] <= 60, f"a moldura voltou a crescer: {topo['height']}px"

    for morto in (".sidebar", ".main-header", ".workflow-steps"):
        assert pagina.locator(morto).count() == 0 or not pagina.locator(morto).first.is_visible(), (
            f"{morto} voltou à tela"
        )


def test_o_palco_usa_a_largura_toda(pagina_do_editor):
    """A barra lateral gastava 250 px de 1366 para mostrar um cartão."""
    pagina, _ = pagina_do_editor
    palco = pagina.locator(".ambientes").bounding_box()
    assert palco["x"] < 40, f"algo voltou a empurrar o conteúdo para a direita: x={palco['x']}"
    assert palco["width"] > 1280, f"o conteúdo só tem {palco['width']}px de 1366"


def test_o_inspetor_vazio_nao_ocupa_a_tela(pagina_do_editor):
    """Ele passava o dia dizendo "Nada selecionado" em 450 px de tela."""
    pagina, _ = pagina_do_editor
    inspetor = pagina.locator("#inspetor")
    if inspetor.count():
        assert not inspetor.first.is_visible(), (
            "o inspetor está visível sem nada selecionado"
        )


def test_a_previa_aberta_encolhe_o_palco_em_vez_de_cobri_lo(pagina_do_editor):
    """Um `width: 100%` meu fazia o palco transbordar em vez de encolher.

    A prévia é um painel fixo de 330 px na direita. O estilo antigo devolvia a
    largura com `margin-right`, mas eu tinha fixado `width: 100% !important` no
    palco: ele media a tela inteira E ainda ganhava a margem, então passava por
    baixo do painel. O canto direito do topo — versão, tema, ajuda — ficava
    embaixo da prévia, inalcançável. Só a foto da tela mostrou.
    """
    pagina, _ = pagina_do_editor
    largura_livre = pagina.locator(".topo").bounding_box()["width"]
    pagina.evaluate(
        """() => {
            document.getElementById('playerDock').classList.add('is-open');
            document.querySelector('.main-content').classList.add('dock-open');
        }"""
    )
    time.sleep(0.4)
    com_previa = pagina.locator(".topo").bounding_box()["width"]
    dock = pagina.locator("#playerDock").bounding_box()["width"]
    pagina.evaluate(
        """() => {
            document.getElementById('playerDock').classList.remove('is-open');
            document.querySelector('.main-content').classList.remove('dock-open');
        }"""
    )
    time.sleep(0.3)
    assert com_previa < largura_livre - dock + 10, (
        f"o topo continuou com {com_previa}px atrás de uma prévia de {dock}px: "
        "o canto direito fica inalcançável"
    )


def test_o_mapa_poe_cada_corte_no_lugar_certo(pagina_do_editor):
    """Um mapa fora de escala mente com confiança; este confere a régua."""
    pagina, _ = pagina_do_editor
    assert pagina.locator("#mapaFonte").is_visible(), "o mapa não apareceu"

    blocos = pagina.locator('.mapa-pista[data-pista="entregues"] .mapa-bloco')
    assert blocos.count() == len(CORTES), (
        f"{blocos.count()} blocos para {len(CORTES)} cortes"
    )

    trilho = pagina.locator('.mapa-pista[data-pista="entregues"] .mapa-trilho').bounding_box()
    # O corte que começa em 87,7s de 1772,1s tem de cair a 5% da régua.
    primeiro = CORTES[4]
    caixa = pagina.locator(
        f'.mapa-pista[data-pista="entregues"] .mapa-bloco[data-corte="4"]'
    ).bounding_box()
    esperado = trilho["x"] + trilho["width"] * (primeiro["start"] / FONTE_S)
    assert abs(caixa["x"] - esperado) < 6, (
        f"o bloco caiu em {caixa['x']:.0f} e deveria cair em {esperado:.0f}"
    )


def test_o_mapa_separa_o_engolido_da_perda(pagina_do_editor):
    """A única pergunta que o mapa precisa responder.

    Um candidato inteiro dentro de um corte entregue não é perda — o corte longo
    contém aquela fala, e o editor já disse que em resposta longa prefere o
    contexto inteiro. Um que só encostava na borda é outra coisa. Dar o mesmo
    desenho para os dois seria repetir o defeito do contador antigo, que dava o
    mesmo "1" para as duas situações.
    """
    pagina, _ = pagina_do_editor
    dentro = pagina.locator('.mapa-pista[data-pista="descartados"] .mapa-bloco[data-dentro="sim"]')
    fora = pagina.locator('.mapa-pista[data-pista="descartados"] .mapa-bloco[data-dentro="nao"]')
    assert dentro.count() == 1 and fora.count() == 1

    estilo = pagina.evaluate(
        """() => {
            const d = document.querySelector('.mapa-bloco[data-dentro="sim"]');
            const f = document.querySelector('.mapa-bloco[data-dentro="nao"]');
            const cs = (n) => getComputedStyle(n);
            return {
                dentroTemHachura: cs(d).backgroundImage.includes("repeating-linear-gradient"),
                foraTemHachura: cs(f).backgroundImage.includes("repeating-linear-gradient"),
                dentroOpacidade: Number(cs(d).opacity),
                foraOpacidade: Number(cs(f).opacity),
            };
        }"""
    )
    assert estilo["dentroTemHachura"], "o engolido tem de ser hachurado, não sólido"
    assert not estilo["foraTemHachura"], "a perda de verdade tem de ser sólida"
    assert estilo["dentroOpacidade"] < estilo["foraOpacidade"], (
        "o que ele já tem não pode competir com o que ele perdeu"
    )


def test_o_resumo_do_mapa_bate_com_os_numeros(pagina_do_editor):
    """A frase que ele lê antes de olhar para qualquer bloco."""
    pagina, _ = pagina_do_editor
    resumo = pagina.locator(".mapa-resumo").inner_text()
    assert "11 corte" in resumo, resumo
    # 29min32 de fonte; a cobertura tem de ser menor e citada em minutos.
    assert "29min32" in resumo, resumo
    assert "1 candidato" in resumo and "encostar" in resumo, (
        f"o resumo não separa a perda real do engolido: {resumo}"
    )


def test_clicar_num_bloco_leva_o_player_ate_ele(pagina_do_editor):
    """Pedido dele: "ao clicar nos blocos deve transportar a pessoa para o
    player original no lugar do bloco"."""
    pagina, _ = pagina_do_editor
    pagina.evaluate(
        """() => {
            let v = document.querySelector('#playerDock video, #videoPreview video, video');
            if (!v) { v = document.createElement('video'); document.body.appendChild(v); }
            v.__marcado = true;
            Object.defineProperty(v, 'currentTime', {
                configurable: true,
                get() { return this.__t || 0; },
                set(valor) { this.__t = valor; },
            });
        }"""
    )
    pagina.locator('.mapa-bloco[data-corte="4"]').click()
    time.sleep(0.3)
    onde = pagina.evaluate(
        "document.querySelector('#playerDock video, #videoPreview video, video').currentTime"
    )
    assert abs(onde - CORTES[4]["start"]) < 1, (
        f"o player foi para {onde}s e o corte começa em {CORTES[4]['start']}s"
    )


def test_o_tema_claro_existe_e_o_botao_o_encontra(pagina_do_editor):
    """"nem sei onde altero para o tema branco" — não sabia porque não havia."""
    pagina, _ = pagina_do_editor
    botao = pagina.locator("#btnTema")
    assert botao.is_visible(), "o botão de tema não está na tela"

    def tinta():
        return pagina.evaluate(
            "getComputedStyle(document.querySelector('.ambiente-intro h2')).color"
        )

    escuro = tinta()
    botao.click()
    time.sleep(0.3)
    claro = tinta()
    assert pagina.evaluate("document.documentElement.dataset.tema") == "claro"
    assert claro != escuro, "o tema mudou de nome mas não de cor"
    # O defeito antigo: o título usava preenchimento em gradiente, desenhado
    # para brilhar sobre preto, e sumia no claro.
    assert claro.startswith("rgb(2") or claro.startswith("rgb(1"), (
        f"o título ficou claro sobre fundo claro: {claro}"
    )
    botao.click()
    time.sleep(0.2)
