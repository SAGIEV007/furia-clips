"""As quatro leis do Furia 2, escritas como teste.

O Furia 1 foi redesenhado quatro vezes e as quatro voltaram parecidas. O motivo
não foi falta de cor nova: foi que as decisões do desenho não estavam escritas
em lugar nenhum, então cada rodada reinventava as mesmas por baixo de tinta
diferente. Aqui elas estão escritas onde quebram sozinhas.

As leis, do docs/CONCEITO-FURIA-2.md:

    1. Cor é informação, nunca decoração.
    2. Ferramenta é objeto, não aba.
    3. O programa liga, não carrega.
    4. Tudo que aparece responde a uma pergunta do corte.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BANCADA = RAIZ / "furia2" / "templates" / "bancada.html"
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"

# Os seis objetos da doca, na ordem em que ficam na prateleira.
OBJETOS = ["fonte", "talho", "mapa", "painel", "ajustes", "registro"]


def html():
    return BANCADA.read_text(encoding="utf-8")


def css():
    return CSS.read_text(encoding="utf-8")


def js():
    return JS.read_text(encoding="utf-8")


def sem_comentario(texto, abre="/*", fecha="*/"):
    """O texto sem os comentários.

    Três testes deste arquivo reprovaram na primeira execução por lerem a
    própria explicação escrita logo acima da regra — o comentário que diz
    "não usar `vh`" contém `vh`. Já aconteceu duas vezes no Furia 1, e a
    correção certa nunca é afrouxar o teste: é olhar só para o código.
    """
    saida, resto = [], texto
    while abre in resto:
        antes, _, depois = resto.partition(abre)
        saida.append(antes)
        _, _, resto = depois.partition(fecha)
    saida.append(resto)
    return "".join(saida)


def satura(valor):
    """Quanto de cor tem neste valor, de 0 (cinza puro) a 1.

    Medir pela DIFERENÇA entre canais reprova o branco de folha, que é quente
    de propósito: #f2efe6 tem 12 pontos de diferença e nenhuma cor. O que
    separa cinza de cor é a diferença em relação ao brilho — a folha dá 5%,
    o fósforo dá 74%.
    """
    v = valor.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    maior = max(r, g, b)
    return 0.0 if maior == 0 else (maior - min(r, g, b)) / maior


# ── lei 1 — cor é informação ────────────────────────────────────────────────


def test_o_programa_tem_exatamente_duas_cores():
    """Preto, cinzas e branco não contam: são a interface. Cor conta.

    Este é o teste que teria pego a rodada em que o âmbar do Furia velho
    voltou sozinho. Se alguém acrescentar uma terceira cor, quebra aqui, e
    quebrar aqui é a única forma de a decisão sobreviver a quem não leu o
    conceito.
    """
    folha = sem_comentario(css())
    # Só interessa o que está declarado como token: é de lá que todo o resto bebe.
    tokens = dict(re.findall(r"(--f2-[a-z0-9]+):\s*(#[0-9a-fA-F]{3,8})", folha))
    assert tokens, "os tokens sumiram; sem eles a paleta volta a ser opinião de cada regra"

    coloridos = sorted(nome for nome, valor in tokens.items() if satura(valor) > 0.15)
    assert coloridos == ["--f2-fosforo", "--f2-sangue"], (
        f"o programa inteiro tem duas cores: fósforo e sangue. Achei {coloridos}"
    )


def test_nenhuma_cor_entra_por_fora_do_token():
    """Não adianta a paleta ser de duas cores se as regras escreverem outras.

    Foi assim que o Furia 1 juntou treze cores sem ninguém decidir nenhuma.
    """
    folha = sem_comentario(css())
    sem_tokens = folha.split("}", 1)[1] if "}" in folha else folha
    for cru in re.findall(r"#[0-9a-fA-F]{3,8}", sem_tokens):
        assert satura(cru) <= 0.15, (
            f"a cor {cru} foi escrita solta numa regra em vez de sair de um token"
        )


def test_o_fundo_e_preto_de_verdade():
    """Cinza-escuro faz miniatura de vídeo parecer suja. Preto faz ela acender."""
    assert re.search(r"--f2-breu:\s*#000000", css()), (
        "o breu deixou de ser preto puro, e a parede de cortes depende disso"
    )


def test_a_faixa_de_cima_so_acende_quando_a_maquina_trabalha():
    """O verde é a máquina falando. Em repouso, a tela inteira é cinza."""
    folha = css()
    for regra in ("body.f2-trabalhando .f2-estado",
                  "body.f2-trabalhando .f2-marca .f2-pulso",
                  "body.f2-trabalhando .f2-contador"):
        assert regra in folha, f"{regra} sumiu: a faixa parou de reagir à operação"
    # E em repouso ela tem de estar apagada de propósito, não por acidente.
    assert re.search(r"\.f2-estado\s*\{[^}]*color:\s*var\(--f2-c5\)", folha, re.DOTALL)


# ── lei 2 — ferramenta é objeto, não aba ────────────────────────────────────


def test_a_doca_tem_os_seis_objetos_com_o_nome_escrito():
    """Ícone sozinho é adivinhação, e ele não vai adivinhar trezentas vezes ao dia."""
    pagina = html()
    for nome in OBJETOS:
        assert f'data-objeto="{nome}"' in pagina, f"o objeto {nome} sumiu da doca"
        assert f'<span class="f2-nome">{nome}</span>' in pagina, (
            f"o objeto {nome} ficou só com o desenho; falta o nome por extenso"
        )


def test_nao_existe_aba_nem_coluna_fixa():
    """O centro da tela é sempre dos cortes.

    A moldura do Furia 1 gastava um quinto da largura numa barra lateral e mais
    um terço numa coluna de detalhe que passava o dia escrito "Nada
    selecionado". Num notebook de 1366 isso é metade da tela.
    """
    folha = css()
    assert "grid-template-rows:" in folha, "a moldura deixou de ser três faixas empilhadas"
    assert "grid-template-columns: 1fr auto 1fr" in folha, (
        "a faixa de cima perdeu a divisão em três; o estado sai do centro"
    )
    proibidos = ["sidebar", "rail-tab", "ambientes", "inspetor"]
    for peca in proibidos:
        assert peca not in sem_comentario(folha), f"'{peca}' é peça da moldura velha e voltou para o Furia 2"


def test_nada_nasce_aberto():
    """Janela que nasce aberta é coluna fixa com outro nome."""
    pagina = html()
    assert 'aria-pressed="true"' not in pagina, (
        "algum objeto já começa marcado como aberto"
    )


# ── lei 3 — o programa liga, não carrega ────────────────────────────────────


def test_a_ignicao_acontece_uma_vez_por_sessao_e_pode_ser_pulada():
    codigo = js()
    assert "sessionStorage" in codigo, "a ignição voltaria a cada tela aberta"
    for saida in ('addEventListener("keydown", apagar)',
                  'addEventListener("mousedown", apagar)'):
        assert saida in codigo, (
            "a ignição ficou obrigatória; abertura que não se pula é abertura que se odeia"
        )


def test_a_ignicao_nao_escreve_o_nome_do_programa():
    """A marca está se juntando do pó ao lado. Escrever ao lado é assinar duas vezes."""
    codigo = js()
    caixa = codigo[codigo.find("f2-caixa-ficha"):codigo.find("f2-pular")]
    assert ">furia<" not in caixa.lower(), (
        "o nome voltou a ser escrito em fonte de sistema ao lado do desenho da marca"
    )


# ── lei 4 — tudo responde a uma pergunta do corte ───────────────────────────


def test_a_marca_e_desenhada_e_nao_depende_de_fonte_baixada():
    """O programa abre sem internet numa máquina Windows.

    Fonte da web é arquivo que falta, que não cabe no instalador, ou que chega
    tarde e faz a tela pular na primeira abertura.
    """
    pagina = html()
    assert "<svg" in pagina and 'aria-label="Furia"' in pagina, "a marca deixou de ser desenhada"

    # Toda origem de arquivo da página tem de ser (a) do próprio programa ou
    # (b) escrita ali dentro. Procurar a palavra "http" não serve: o endereço
    # `http://www.w3.org/2000/svg` é o nome do formato SVG, não um download —
    # ele aparece em toda marca desenhada e nunca sai da máquina.
    for atributo, valor in re.findall(r'\b(href|src)="([^"]*)"', pagina):
        de_casa = valor.startswith("data:") or "url_for(" in valor
        assert de_casa, f"{atributo}=\"{valor[:60]}\" busca arquivo fora do programa"

    folha = sem_comentario(css())
    for fora in ("@import", "url(http", "fonts.googleapis", "fonts.gstatic"):
        assert fora not in folha, f"a folha de estilo passou a buscar {fora} na rede"


def test_nenhum_botao_da_doca_falha_calado():
    """Botão que não faz nada e não fala é o defeito mais caro deste programa.

    O ajuste de corte gravou o valor errado por duas versões devolvendo 200; a
    prévia fechava num elemento apagado. Os dois eram silêncio. Enquanto os
    objetos não abrem, eles têm de DIZER que ainda não abrem.
    """
    codigo = js()
    assert "ainda não montado" in codigo, (
        "o objeto que ainda não existe voltou a não responder ao clique"
    )
    assert "MONTADO" in codigo, (
        "sumiu o lugar onde cada tela nova registra o seu objeto"
    )


def test_a_altura_da_faixa_e_da_doca_e_fixa():
    """`vh` solto no Windows com barra de tarefas mede errado e joga a doca para fora."""
    folha = sem_comentario(css())
    assert re.search(r"--f2-faixa:\s*\d+px", folha)
    assert re.search(r"--f2-doca:\s*\d+px", folha)
    assert "vh" not in folha, "voltou medida de altura de janela; a doca sai da tela"


def test_a_bancada_vazia_diz_por_onde_comecar():
    """Tela preta sem nada escrito não é austeridade: é abandono."""
    pagina = html()
    assert "bancada vazia" in pagina
    assert "puxe a fonte da doca" in pagina
    assert 'body.f2-bancada-vazia .f2-objeto[data-objeto="fonte"]' in css(), (
        "o convite sumiu do lugar onde ele é executado"
    )
