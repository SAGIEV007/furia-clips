"""O detector de abertura aprovava TODAS as aberturas, inclusive as ruins.

O editor avaliou os onze cortes da PENÉLOPE um a um e disse que aproveitaria
7 ou 8. O que estragava os outros era sempre a borda: começar no meio do
raciocínio, ou terminar sem concluí-lo.

Antes de escrever uma linha eu rodei os detectores REAIS contra as onze
aberturas e os onze fechos daquela corrida. O resultado foi o diagnóstico
inteiro:

    aberturas que acionavam o recuo:  0 de 11
    cortes marcados com contexto incompleto: 0 de 11

Zero. O predicado de reparo dizia que todas as onze aberturas "começam um
pensamento", inclusive estas cinco:

    #6  "Agora eu não sei o que que vocês estão avaliando…"
    #9  "Somando tudo a três pontos na redondado,"
    #7  "Quatro debates organizados aí."
    #10 "O Renan também criticou Flávio Bolsonaro…"
    #3  "Está certo? O Lula tem que estar nos debates…"

Como ele nunca dizia "isto não começa nada", o recuo nunca andava. Não era o
recuo que estava quebrado — era a pergunta que ele fazia antes de andar.

As cinco falham por GRAMÁTICA, não por assunto, e é isso que permite detectá-las
sem inventar limiar: oração gerundiva é subordinada por construção; "também"
afirma "além de algo" que ficou atrás; "aí" no fim da oração aponta para fora do
corte; "agora" na primeira palavra contrasta com o que veio antes; um fragmento
de três palavras terminado em "?" responde a algo.

── por que o REPARO e não o PORTÃO ──────────────────────────────────────────

O mesmo texto passa por dois lugares: `_editorial_flags`, que ADIA candidatos, e
`_opens_a_thought`, que MOVE bordas. Alargar o primeiro faria mais candidatos
serem adiados, e o editor foi explícito: "me dê certeza que isso não reduz a
quantidade de cortes". Alargar o segundo faz o corte começar mais cedo, que é a
direção que ele prefere — "em casos de respostas longas eu gostaria de ter o
contexto inteiro porque aí eu mesmo edito" — e o recuo tem orçamento próprio.
Só o reparo mudou.

── o outro lado da borda ────────────────────────────────────────────────────

O avanço de fecho só sabe SOMAR. Quando o rabo de assunto novo já nasceu dentro
do bloco, nenhum passo o removia — daí o corte que termina em "segundo ponto:".

E "se sustenta sozinha" não separa nada nesse lado: um fim BOM também é uma
frase que se sustenta sozinha. Foi justamente por isso que o avanço nunca pegou
o caso. O que separa é a marca de anúncio.
"""

import pytest

from modules.clip_selector import ClipSelector


@pytest.fixture
def seletor():
    return ClipSelector()


# ── as cinco aberturas reais que passavam batido ───────────────────────────

@pytest.mark.parametrize(
    "abertura",
    [
        pytest.param("Agora eu não sei o que que vocês estão avaliando, mas eu acho",
                     id="agora-contrasta-com-o-que-veio-antes"),
        pytest.param("Somando tudo a três pontos na redondado,",
                     id="gerundio-e-oracao-subordinada"),
        pytest.param("Quatro debates organizados aí.",
                     id="ai-no-fim-da-oracao-aponta-para-fora"),
        pytest.param("O Renan também criticou Flávio Bolsonaro por ter ido a barretos",
                     id="tambem-pressupoe-um-item-anterior"),
        pytest.param("Está certo?", id="fragmento-curto-responde-algo-atras"),
    ],
)
def test_abertura_ruim_aciona_o_recuo(seletor, abertura):
    assert not seletor._opens_a_thought(abertura), (
        "esta abertura passou pelo detector e o recuo não vai andar"
    )


# ── e as boas, que não podem ser tocadas ───────────────────────────────────

@pytest.mark.parametrize(
    "abertura",
    [
        pytest.param("O político hoje quer expor as suas mentiras, as suas lorotas,",
                     id="sujeito-proprio"),
        pytest.param("Pernoera falou, não é uma entrevista de emprego.",
                     id="traz-o-referente-junto"),
        pytest.param("Pode me perguntar de qualquer assunto, apresentei um livro de propostas",
                     id="convite-se-sustenta"),
        pytest.param("Eu quero debater com quem não acredita em Deus, porque quando eu for",
                     id="primeira-pessoa-com-tese"),
        pytest.param("Lá em Brasília o orçamento foi aprovado sem debate.",
                     id="la-com-referente-proprio-nao-e-deitico"),
        pytest.param("O senhor aceita participar do debate na Band?",
                     id="pergunta-longa-e-hook-nao-fragmento"),
    ],
)
def test_abertura_boa_continua_valendo(seletor, abertura):
    assert seletor._opens_a_thought(abertura), (
        "o detector alargou demais e vai recuar uma abertura que já estava certa"
    )


# ── o fecho que anuncia em vez de concluir ─────────────────────────────────

@pytest.mark.parametrize(
    "fecho",
    [
        pytest.param("Segundo ponto:", id="enumeracao-pendurada"),
        pytest.param("Outro ponto importante:", id="enumeracao-com-dois-pontos"),
        pytest.param("Eu tive essa experiência uma vez no Arontalcus.",
                     id="uma-vez-abre-causo"),
        pytest.param("Teve um caso em Minas que mostra isso.",
                     id="referente-indefinido-novo"),
    ],
)
def test_fecho_que_anuncia_e_reconhecido(seletor, fecho):
    assert seletor._announces_a_new_subject(fecho)


@pytest.mark.parametrize(
    "fecho",
    [
        pytest.param("Eu vou falar do que quiser.", id="desafio-e-fecho-otimo"),
        pytest.param("Debates são confrontos de ideias.", id="definicao-fecha"),
        pytest.param("É isso que o Brasil precisa entender.", id="conclusao"),
        pytest.param("para quem ele quiser dar o voto, para escolher.",
                     id="fim-real-do-corte-1"),
    ],
)
def test_fecho_bom_nao_e_aparado(seletor, fecho):
    assert not seletor._announces_a_new_subject(fecho), (
        "o detector vai cortar um fecho que já estava bom"
    )


# ── o aparo em si ──────────────────────────────────────────────────────────

def _frases(itens):
    return [{"start": de, "end": ate, "text": texto} for de, ate, texto in itens]


def test_o_aparo_tira_so_a_ultima_frase(seletor):
    frases = _frases([
        (100.0, 118.0, "O debate é o único lugar onde o candidato não controla a pergunta."),
        (118.0, 140.0, "Quem foge dele está dizendo que não quer ser confrontado."),
        (140.0, 146.0, "Eu tive essa experiência uma vez no Arontalcus."),
    ])
    cortes = [{"start": 100.0, "end": 146.0, "duration": 46.0, "text": "x"}]
    seletor._trim_trailing_announcement(cortes, frases)

    assert cortes[0]["end"] == pytest.approx(140.0)
    assert cortes[0]["duration"] == pytest.approx(40.0)
    assert cortes[0]["closing_trimmed_s"] == pytest.approx(6.0)
    assert "Arontalcus" not in cortes[0]["text"]
    assert "não quer ser confrontado" in cortes[0]["text"]


def test_o_aparo_nao_encolhe_abaixo_do_minimo(seletor):
    """Um corte aparado continua existindo; um corte curto demais, não.

    A garantia que o editor pediu — "nada pode reduzir a quantidade de cortes" —
    depende deste piso. Sem ele o aparo poderia derrubar um corte no chão da
    renderização, que seria reduzir a quantidade por via indireta.
    """
    frases = _frases([
        (100.0, 106.0, "O debate é onde o candidato não controla a pergunta."),
        (106.0, 112.0, "Eu tive essa experiência uma vez no Arontalcus."),
    ])
    cortes = [{"start": 100.0, "end": 112.0, "duration": 12.0, "text": "x"}]
    seletor._trim_trailing_announcement(cortes, frases)

    assert cortes[0]["end"] == pytest.approx(112.0), (
        "aparou até abaixo da duração mínima e o corte pode sumir na renderização"
    )
    assert "closing_trimmed_s" not in cortes[0]


def test_o_aparo_nao_toca_num_fecho_bom(seletor):
    frases = _frases([
        (100.0, 130.0, "Quem foge do debate está dizendo que não quer ser confrontado."),
        (130.0, 160.0, "Debates são confrontos de ideias, e é isso que eles temem."),
    ])
    cortes = [{"start": 100.0, "end": 160.0, "duration": 60.0, "text": "x"}]
    seletor._trim_trailing_announcement(cortes, frases)
    assert cortes[0]["end"] == pytest.approx(160.0)


def test_um_corte_de_uma_frase_so_fica_inteiro(seletor):
    """Aparar a única frase deixaria um corte de duração zero."""
    frases = _frases([(100.0, 160.0, "Eu tive essa experiência uma vez no Arontalcus.")])
    cortes = [{"start": 100.0, "end": 160.0, "duration": 60.0, "text": "x"}]
    seletor._trim_trailing_announcement(cortes, frases)
    assert cortes[0]["end"] == pytest.approx(160.0)


def test_nenhum_corte_desaparece_no_aparo(seletor):
    """A promessa que o editor cobrou, verificada como contagem."""
    frases = _frases([
        (0.0, 30.0, "Primeira fala completa e autossuficiente sobre o tema."),
        (30.0, 60.0, "Segunda fala completa e autossuficiente sobre o tema."),
        (60.0, 66.0, "Eu tive essa experiência uma vez no Arontalcus."),
        (66.0, 100.0, "Terceira fala completa e autossuficiente sobre o tema."),
        (100.0, 106.0, "Segundo ponto:"),
    ])
    cortes = [
        {"start": 0.0, "end": 66.0, "duration": 66.0, "text": "x"},
        {"start": 66.0, "end": 106.0, "duration": 40.0, "text": "y"},
    ]
    antes = len(cortes)
    devolvidos = seletor._trim_trailing_announcement(cortes, frases)
    assert len(devolvidos) == antes
    assert all(c["end"] > c["start"] for c in devolvidos)
