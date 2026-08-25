"""O painel: 29.596 posts medidos que o editor nunca tinha visto.

Eles estavam num arquivo. Saber que `news-peg` rende 1,40 contra 0,98 da
`tese-provocativa` muda o que se grava e o que se corta — e isso estava escrito
só em JSON, onde ninguém lê.

O que estes testes protegem é a honestidade do desenho, não a aparência:

A conta é sempre contra a mediana da própria conta, então 1,00 é a origem da
escala e o que importa é a distância até ali. Um painel que mostrasse o valor
bruto não diria nada.

O tamanho da amostra viaja com o número, sempre. `contraste-regional` marca
1,19 com quatro exemplos e `tese-provocativa` marca 0,98 com quatrocentos e
oitenta e dois; desenhar as duas barras sem dizer isso seria mentir com a
verdade.

E nada aqui é medição do próprio Furia — são posts que foram ao ar e blocos que
uma pessoa revisou.
"""

from pathlib import Path

import pytest

import app as aplicacao

PAINEL_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "painel.js"
ATELIE_CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "atelie.css"


@pytest.fixture(scope="module")
def painel():
    resposta = aplicacao.app.test_client().get("/api/painel")
    assert resposta.status_code == 200
    return resposta.get_json()


def test_o_painel_desenha_a_amostra_de_verdade(painel):
    assert painel["espelho"]["disponivel"] is True
    assert painel["espelho"]["posts_com_desempenho"] >= 29000
    assert len(painel["ganchos"]) >= 8


def test_os_ganchos_vem_ordenados_do_melhor_para_o_pior(painel):
    medianas = [g["mediana"] for g in painel["ganchos"]]
    assert medianas == sorted(medianas, reverse=True)
    assert painel["ganchos"][0]["familia"] == "news-peg"


def test_todo_numero_carrega_o_tamanho_da_amostra(painel):
    """Sem o n, 1,19 com quatro exemplos parece tão firme quanto 0,98 com 482."""
    for item in painel["ganchos"] + painel["temas"]["melhores"] + painel["temas"]["piores"]:
        assert int(item["n"]) >= 3


def test_o_piso_de_amostra_e_respeitado_no_painel(painel):
    """Tema com menos de oito exemplos não vira barra."""
    for item in painel["temas"]["melhores"] + painel["temas"]["piores"]:
        assert int(item["n"]) >= 8


def test_os_temas_piores_vem_do_pior_para_o_menos_pior(painel):
    medianas = [t["mediana"] for t in painel["temas"]["piores"]]
    assert medianas == sorted(medianas)


def test_o_mapa_de_nomes_declara_a_duvida(painel):
    """Quinze nomes aparecem quase tanto de um lado quanto do outro.

    Esconder isso e mostrar só os adversários "certos" transformaria um empate
    de 62 a 60 numa afirmação que o dado não sustenta.
    """
    assert painel["papeis"]["adversarios"] > 0
    assert "Romeu Zema" in painel["papeis"]["indefinidos"]
    for item in painel["papeis"]["principais"]:
        assert item["lado"] == "adversario"
        assert item["confianca"] >= 0.7


def test_trocar_de_conta_troca_os_numeros():
    cliente = aplicacao.app.test_client()
    principal = cliente.get("/api/painel?conta=@renansantosmbl").get_json()
    reserva = cliente.get("/api/painel?conta=@renansantosreserva").get_json()
    assert reserva["conta"] == "@renansantosreserva"
    assert principal["ganchos"] != reserva["ganchos"], (
        "as contas têm bases próprias e nunca podem ser misturadas"
    )


def test_uma_conta_que_nao_existe_devolve_vazio_e_nao_erro():
    corpo = aplicacao.app.test_client().get("/api/painel?conta=@ninguem").get_json()
    assert corpo["ganchos"] == []
    assert corpo["temas"]["melhores"] == []


def test_a_escala_e_divergente_e_o_meio_e_neutro():
    """1,00 é a origem: acima e abaixo são direções opostas, não intensidades."""
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert "--viz-acima" in css and "--viz-abaixo" in css and "--viz-meio" in css
    assert ".faixa-barra.acima" in css and ".faixa-barra.abaixo" in css
    # O ouro é o acento da interface e não pode virar cor de dado: o olho
    # confundiria "isto é do Furia" com "isto rendeu bem".
    bloco = css[css.find("--viz-acima"):css.find("--viz-acima") + 400]
    assert "--at-ouro" not in bloco


def test_a_regua_nao_empilha_os_rotulos_na_mesma_celula():
    """Os três rótulos ocupavam a MESMA célula da grade, um por cima do outro.

    Numa coluna larga o alinhamento disfarçava; nos cartões estreitos saía
    "MENOSQUE1,00TÍPICO" embaralhado.
    """
    css = ATELIE_CSS.read_text(encoding="utf-8")
    assert ".regua-eixos" in css
    assert "grid-template-columns: 1fr auto 1fr" in css


def test_sigla_de_estado_vira_nome_de_estado():
    """"uf-pa" virava "Pa" — um enigma no meio de um gráfico."""
    js = PAINEL_JS.read_text(encoding="utf-8")
    assert 'pa: "Pará"' in js
    assert 'sp: "São Paulo"' in js
    assert 'saude: "Saúde"' in js


def test_o_painel_nao_busca_nada_fora():
    """O programa abre sem internet."""
    for arquivo in (PAINEL_JS, ATELIE_CSS):
        texto = arquivo.read_text(encoding="utf-8")
        for marca in ("https://", "http://"):
            assert marca not in texto
