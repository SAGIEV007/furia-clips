"""O player não pode nascer dentro de uma janela fechada.

O editor relatou duas vezes que "o player simplesmente SUMIU". As duas vezes eu
procurei no JavaScript, porque é onde um clique que não responde costuma morrer.
Não estava lá. O player abria certo — a classe `is-open` entrava, o vídeo era
baixado com HTTP 206, nenhum erro no console — e media 0 × 0 pixel.

A causa estava no HTML, a uma tag de distância:

    </div>      <!-- fecha .modal -->
    </main>     <!-- deveria ser </div>, fechando #subtitleModal -->

O `<main>` abria uma vez e fechava duas. Com o `</main>` no lugar do `</div>`, o
modal de legendas nunca fechava, e todo o resto do arquivo — a começar pelo
player — virava filho de um elemento com `display: none`. Filho de `display:none`
não ocupa espaço, e do lado de fora parece que o clique não fez nada.

Nenhum erro de JavaScript apareceria jamais. É por isso que estes testes olham a
árvore do documento, e não o comportamento: o defeito era de estrutura, e
estrutura se confere lendo o arquivo.
"""

from html.parser import HTMLParser
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

# Tags que se fecham sozinhas e não entram na conta de aninhamento.
VAZIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
          "link", "meta", "param", "source", "track", "wbr"}


class Arvore(HTMLParser):
    """Guarda, para cada elemento com id, a pilha de ancestrais até ele."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pilha = []
        self.ancestrais_de = {}
        self.contagem = {}

    def handle_starttag(self, tag, attrs):
        self.contagem[tag] = self.contagem.get(tag, 0) + 1
        if tag in VAZIAS:
            return
        atributos = dict(attrs)
        identificador = atributos.get("id")
        classe = atributos.get("class", "")
        if identificador:
            self.ancestrais_de[identificador] = list(self.pilha)
        self.pilha.append({"tag": tag, "id": identificador, "class": classe})

    def handle_endtag(self, tag):
        if tag in VAZIAS:
            return
        for posicao in range(len(self.pilha) - 1, -1, -1):
            if self.pilha[posicao]["tag"] == tag:
                del self.pilha[posicao:]
                return


@pytest.fixture(scope="module")
def arvore():
    parser = Arvore()
    parser.feed(TEMPLATE.read_text(encoding="utf-8"))
    return parser


def test_o_player_nao_esta_dentro_de_um_modal(arvore):
    """Um modal fica com `display: none` fechado; quem mora dentro some junto."""
    ancestrais = arvore.ancestrais_de.get("playerDock")
    assert ancestrais is not None, "o player sumiu do template"
    dentro_de = [
        f"{no['tag']}#{no['id'] or '?'}"
        for no in ancestrais
        if "modal" in (no["class"] or "")
    ]
    assert not dentro_de, (
        f"o player está dentro de {', '.join(dentro_de)} — um elemento que fica "
        f"escondido enquanto o modal está fechado, então o player abre com 0 pixel"
    )


def test_o_player_e_filho_direto_do_corpo(arvore):
    """Ele é fixo na tela; qualquer pai extra pode limitá-lo sem aviso.

    Não é preciosismo: um pai com `overflow`, `transform` ou `display` próprio
    muda o comportamento de um elemento `position: fixed` sem produzir erro
    nenhum. Fora do corpo, o defeito volta calado.
    """
    ancestrais = arvore.ancestrais_de.get("playerDock") or []
    caminho = [no["tag"] for no in ancestrais]
    assert caminho == ["html", "body"], f"o player está aninhado em {caminho}"


def test_as_tags_de_main_estao_equilibradas():
    """Foi um `</main>` a mais que empurrou o player para dentro do modal."""
    texto = TEMPLATE.read_text(encoding="utf-8")
    aberturas = texto.count("<main")
    fechamentos = texto.count("</main>")
    assert aberturas == fechamentos, (
        f"{aberturas} <main> aberto(s) e {fechamentos} fechado(s); um fechamento "
        f"sobrando fecha o elemento errado e reparenta tudo o que vem depois"
    )


def test_a_janela_de_legendas_fecha(arvore):
    """O controle: o modal fecha e não engole o que vem depois dele.

    A verificação é por elementos nomeados, não por convenção de nome. As outras
    janelas são irmãs do modal de legendas, e é justamente isso que denuncia o
    defeito: se o `</div>` some, elas deixam de ser irmãs e viram filhas — junto
    com o player, que foi como o problema apareceu para o editor.
    """
    assert "subtitleModal" in arvore.ancestrais_de, "o modal de legendas sumiu"
    irmaos = ["playerDock", "videoPreview", "helpModal", "thumbnailModal"]
    engolidos = [
        identificador for identificador in irmaos
        if "subtitleModal" in [no["id"] for no in arvore.ancestrais_de.get(identificador, [])]
    ]
    assert not engolidos, (
        f"{', '.join('#' + nome for nome in engolidos)} caiu(íram) dentro do modal "
        f"de legendas; o modal não está fechando"
    )
