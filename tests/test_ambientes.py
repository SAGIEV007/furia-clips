"""Quatro ambientes no lugar de doze seções empilhadas — sem perder nada.

O editor: "navegar é mal otimizado e mal organizado", "muito espaço vazio à
direita", "MUITA informação do lado esquerdo". Medido antes de mexer: 74 botões,
34 campos, 23 menus, 273 elementos identificados e 12 seções, tudo numa coluna
só, com a configuração inteira morando na barra lateral o tempo todo.

A reorganização move as seções existentes para ambientes; não reescreve widget
nenhum. É a única forma de reorganizar sem perder função, e a exigência era
explícita: "NÃO PERCA FUNÇÃO".

Estes testes existem para provar isso a cada mudança futura: cada seção tem que
estar em exatamente um ambiente, e o inventário de controles não pode encolher.
"""

from html.parser import HTMLParser
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
ATELIE_CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "atelie.css"
ATELIE_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "atelie.js"
TALHO_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "talho.js"

# Onde cada coisa que existia foi parar. É a lista que o editor pediu.
DESTINOS = {
    "amb-fila": ["sourceSection", "mediaLibrarySection", "operationDashboard"],
    "amb-cortar": ["contextSection", "actionsSection", "sourceReadingSection"],
    "amb-auditoria": ["resultsSection", "headlineStudioSection"],
    "amb-acervo": ["editorialBlocksSection", "performanceMetricsSection"],
}

VAZIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
          "link", "meta", "param", "source", "track", "wbr"}


class Arvore(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pilha = []
        self.ancestrais = {}
        self.controles = {"button": 0, "input": 0, "select": 0, "textarea": 0}

    def handle_starttag(self, tag, attrs):
        if tag in self.controles:
            self.controles[tag] += 1
        if tag in VAZIAS:
            return
        identificador = dict(attrs).get("id")
        if identificador:
            self.ancestrais[identificador] = [no for no in self.pilha]
        self.pilha.append(identificador)

    def handle_endtag(self, tag):
        if tag in VAZIAS or not self.pilha:
            return
        self.pilha.pop()


@pytest.fixture(scope="module")
def arvore():
    parser = Arvore()
    parser.feed(TEMPLATE.read_text(encoding="utf-8"))
    return parser


def test_cada_secao_esta_no_ambiente_certo(arvore):
    for ambiente, secoes in DESTINOS.items():
        for secao in secoes:
            assert secao in arvore.ancestrais, f"{secao} sumiu do documento"
            assert ambiente in arvore.ancestrais[secao], (
                f"{secao} deveria estar em {ambiente} e está em "
                f"{[a for a in arvore.ancestrais[secao] if a and a.startswith('amb-')] or 'nenhum ambiente'}"
            )


def test_nenhuma_secao_aparece_em_dois_ambientes(arvore):
    for secoes in DESTINOS.values():
        for secao in secoes:
            ambientes = [a for a in arvore.ancestrais[secao] if a and a.startswith("amb-")]
            assert len(ambientes) == 1, f"{secao} está dentro de {ambientes}"


def test_o_inventario_de_controles_nao_encolheu(arvore):
    """74 botões, 34 campos e 23 menus era o retrato de antes.

    A reorganização acrescenta controles próprios (as abas, a paleta, a gaveta),
    então o número sobe. O que não pode é cair: cada um desses controles faz
    alguma coisa, e apagar em silêncio é perder função.
    """
    assert arvore.controles["button"] >= 74
    assert arvore.controles["input"] >= 34
    assert arvore.controles["select"] >= 23


def test_o_console_saiu_da_pagina_e_virou_gaveta(arvore):
    """Ele importa quando quebra, não o tempo todo."""
    assert "gavetaCorpo" in arvore.ancestrais["consoleSection"]


def test_a_esquerda_ficou_magra(arvore):
    """Configuração, aparência, voz, motor e pasta são ajustes de uma vez por mês.

    Eles continuam existindo — todos os seus campos seguem no documento — mas
    fora da tela de trabalho.
    """
    for campo in ("settingWhisperModel", "outputDirDisplay", "btnEnrollVoice", "btnSaveSettings"):
        assert campo in arvore.ancestrais, f"{campo} sumiu"
        assert "ajustesFundo" in arvore.ancestrais[campo], (
            f"{campo} voltou a morar na barra lateral"
        )


def test_o_inspetor_existe_e_e_irmao_dos_ambientes(arvore):
    """O espaço vazio da direita virou o painel de detalhe do que está selecionado."""
    assert "inspetor" in arvore.ancestrais
    assert not [a for a in arvore.ancestrais["inspetor"] if a and a.startswith("amb-")]


def test_o_talho_carrega_antes_do_atelie():
    """`talho.js` publica `montarTalho`, e o `app.js` chama isso ao abrir o painel."""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert html.index("/static/js/app.js") < html.index("/static/js/talho.js")


def test_o_painel_de_ajustes_vem_antes_dos_scripts():
    """O app.js liga ouvintes no topo do arquivo.

    Quando a gaveta de ajustes ficou depois das tags de script, o botão da pasta
    de saída ainda não existia no documento e `addEventListener` de `null`
    derrubava o arquivo inteiro na primeira linha — nenhum botão da página
    respondia.
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    assert html.index('id="ajustesFundo"') < html.index("/static/js/app.js")


def test_a_navegacao_antiga_nao_esconde_mais_secoes():
    """Duas navegações na mesma tela brigam.

    O sistema de etapas escondia `resultsSection` enquanto a barra de ambientes
    mostrava a Auditoria, e o cartão do corte nascia com zero pixel — sem erro
    nenhum, como sempre acontece quando o culpado é `display:none`.
    """
    js = (Path(__file__).resolve().parents[1] / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'classList.toggle("stage-off"' not in js


def test_o_claro_cobre_os_fundos_escuros_escritos_na_mao():
    """O estilo antigo pinta 34 lugares com `rgba` escuro em vez de variável.

    No escuro isso some; no claro vira placa cinza por cima do texto. Foi o que
    apareceu no primeiro print: botões de fonte, dica, cartão do vídeo e meta do
    dia, todos ilegíveis.

    ── por que este teste mudou de forma ──────────────────────────────────────

    Ele exigia o texto `[data-theme="light"] .source-tabs` dentro do arquivo. E
    passou verde durante toda a reforma da sala — enquanto as 34 regras estavam
    MORTAS: o tema novo carimba `data-tema="claro"`, e nenhuma das duas condições
    antigas (`body.light-mode`, `[data-theme="light"]`) casava mais com coisa
    alguma. O teste procurava uma string, e a string continuava lá.

    Um teste que só sabe dizer "a linha existe no arquivo" não sabe dizer se ela
    faz alguma coisa. Agora ele exige que a regra seja INCONDICIONAL — sem
    condição não há condição para apodrecer — e que a superfície aponte para um
    papel em vez de uma cor fixa, que é a propriedade que faz os dois temas
    funcionarem.
    """
    css = ATELIE_CSS.read_text(encoding="utf-8")
    for classe in (".source-tabs", ".source-panel", ".selected-video", ".action-card", ".result-card"):
        assert f"\n{classe} {{" in css, (
            f"{classe} perdeu a regra que troca o preenchimento fixo por um papel"
        )
    # E a condição morta não pode voltar por nenhum dos dois nomes.
    for morta in ('[data-theme="light"] .source-tabs', "body.light-mode .source-tabs"):
        assert morta not in css, (
            f"a superfície voltou a depender de {morta!r}, uma condição que o "
            "tema atual nunca carimba"
        )


def test_a_paleta_e_o_talho_nao_dependem_de_rede():
    """O programa abre sem internet; nada aqui pode buscar fonte ou script fora."""
    for arquivo in (ATELIE_CSS, ATELIE_JS, TALHO_JS):
        texto = arquivo.read_text(encoding="utf-8")
        for marca in ("https://", "http://", "@import url("):
            assert marca not in texto, f"{arquivo.name} busca algo fora: {marca}"
