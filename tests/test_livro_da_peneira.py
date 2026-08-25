"""Quem a peneira derruba precisa ter nome, e não só um contador.

O editor pergunta a mesma coisa de duas formas: "estou perdendo cortes?" e "isso
da repórter terminando o corte iniciando uma pergunta não está influenciando
negativamente em outros cortes serem considerados?".

O diagnóstico real da corrida dele respondia com um número e nada mais:

    expected_count 26 · primary_count 24 · final_count 14
    fallback_discarded_overlap  12

Doze o quê? A pergunta só tem resposta se o registro disser QUEM saiu e por
causa de quem. E há dois casos opostos escondidos atrás daquele mesmo "12":

* Um candidato de 40 s inteiramente dentro de um corte de 143 s tem
  sobreposição 1,00 e morre. O editor não perdeu nada — o corte longo contém
  aquela fala, e ele já disse que em respostas longas prefere o contexto
  inteiro.
* Um candidato que só herdou alguns segundos de pergunta da repórter na borda
  tem sobreposição baixa. Esse sobrevive — e este teste mede até onde.

São situações opostas e o contador dava o mesmo "1" para as duas. Agora o
diagnóstico separa, e o registro na tela diz a diferença em português.

Nada aqui muda quem é selecionado: é metadado sobre uma decisão que já era
tomada do mesmo jeito antes.
"""

import pytest

from modules.clip_selector import ClipSelector


def _corte(inicio, fim, texto, pontuacao=70.0):
    return {
        "start": float(inicio),
        "end": float(fim),
        "duration": float(fim - inicio),
        "text": texto,
        "viral_score": pontuacao,
        "editorial_potential_score": pontuacao,
        "confidence": 0.8,
    }


@pytest.fixture
def seletor():
    return ClipSelector()


def test_o_corte_longo_engole_o_curto_e_o_registro_diz_isso(seletor):
    """O caso B, o que realmente custa candidatos na corrida dele."""
    longo = _corte(200, 343, "Resposta longa e completa sobre o tema todo.", 90.0)
    dentro = _corte(270, 310, "Um pedaço da mesma resposta.", 60.0)
    ficaram = seletor._remove_overlaps([longo, dentro])

    assert len(ficaram) == 1
    assert ficaram[0]["start"] == 200

    livro = seletor._candidate_diagnostics["descartados_por_sobreposicao"]
    assert len(livro) == 1
    item = livro[0]
    assert item["motivo"] == "overlap"
    assert item["medida"] == pytest.approx(1.0)
    assert item["dentro_do_vencedor"] is True, (
        "estar inteiro dentro do vencedor é o que separa 'conteúdo que já tenho' "
        "de 'corte perdido'"
    )
    assert item["inicio"] == 270 and item["fim"] == 310
    assert item["vencedor_inicio"] == 200 and item["vencedor_fim"] == 343


def test_a_pergunta_da_reporter_na_borda_nao_mata_o_candidato(seletor):
    """O caso A — o que ele temia — medido em vez de suposto.

    Um corte que termina com a repórter começando a próxima pergunta vaza
    poucos segundos para dentro do candidato seguinte. Dois candidatos de 45 s
    lado a lado, com 6 s de vazamento: 6/45 = 0,13, muito abaixo de 0,30.
    """
    primeiro = _corte(100, 145, "Resposta sobre o primeiro assunto do debate.", 80.0)
    segundo = _corte(139, 184, "Outra resposta, sobre assunto completamente distinto.", 75.0)
    ficaram = seletor._remove_overlaps([primeiro, segundo])

    assert len(ficaram) == 2, (
        "seis segundos de pergunta vazada derrubaram um candidato inteiro"
    )
    assert seletor._candidate_diagnostics["descartados_por_sobreposicao"] == []


@pytest.mark.parametrize("duracao", [20, 30, 45, 60, 90, 120])
def test_seis_segundos_de_vazamento_sobrevivem_em_toda_duracao_util(seletor, duracao):
    """A mesma medição, varrida por tamanho de candidato.

    O limite é 30% do MENOR dos dois. Com 6 s de vazamento, o candidato só morre
    se durar menos de 20 s — abaixo do mínimo que a ferramenta entrega. Em toda
    duração que ele publica, a pergunta na borda é inofensiva.
    """
    vazamento = 6.0
    primeiro = _corte(100, 100 + duracao, "Primeira resposta do bloco.", 80.0)
    segundo = _corte(
        100 + duracao - vazamento,
        100 + duracao - vazamento + duracao,
        "Segunda resposta, outro assunto.",
        75.0,
    )
    assert len(seletor._remove_overlaps([primeiro, segundo])) == 2


def test_o_livro_nao_cresce_sem_limite(seletor):
    """Duas horas de vídeo não podem gerar um JSON que não abre."""
    vencedor = _corte(0, 4000, "Um bloco enorme que engole tudo.", 99.0)
    perdedores = [
        _corte(10 + i * 20, 10 + i * 20 + 15, f"Fragmento numero {i}.", 50.0)
        for i in range(120)
    ]
    seletor._remove_overlaps([vencedor, *perdedores])
    assert len(seletor._candidate_diagnostics["descartados_por_sobreposicao"]) == 60


def test_o_registro_na_tela_separa_engolido_de_perdido():
    """A linha que ele consegue ler sem abrir arquivo nenhum."""
    import app as aplicacao

    linhas = []
    diagnostico = {
        "descartados_por_sobreposicao": [
            {"dentro_do_vencedor": True, "inicio": 270.0, "fim": 310.0, "duracao": 40.0,
             "vencedor_inicio": 200.0, "vencedor_fim": 343.0, "trecho": "pedaço da resposta"},
            {"dentro_do_vencedor": False, "inicio": 500.0, "fim": 555.0, "duracao": 55.0,
             "vencedor_inicio": 540.0, "vencedor_fim": 640.0, "trecho": "outra fala inteira"},
        ]
    }
    aplicacao._anunciar_descartes_por_sobreposicao(
        diagnostico, lambda texto, nivel="info": linhas.append(texto)
    )

    resumo = linhas[0]
    assert "2 trecho(s)" in resumo
    assert "1 estavam inteiros dentro de um corte maior" in resumo
    assert "1 só encostavam na borda" in resumo
    # O que encostou na borda é o que ele pode querer de volta: aparece com hora.
    detalhe = " ".join(linhas[1:])
    assert "8:20" in detalhe and "9:15" in detalhe, detalhe
    assert "outra fala inteira" in detalhe
    assert "pedaço da resposta" not in detalhe, (
        "o que já está dentro de um corte escolhido não é perda e não precisa de linha"
    )


def test_sem_descarte_nao_ha_linha():
    import app as aplicacao

    linhas = []
    aplicacao._anunciar_descartes_por_sobreposicao(
        {"descartados_por_sobreposicao": []}, lambda t, n="info": linhas.append(t)
    )
    aplicacao._anunciar_descartes_por_sobreposicao({}, lambda t, n="info": linhas.append(t))
    assert linhas == []
