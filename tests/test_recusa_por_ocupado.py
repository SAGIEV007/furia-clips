"""A recusa por ocupado tem que dizer o que está rodando.

O editor tentou começar um corte e leu:

    "Já existe um processamento em andamento. Espere ele terminar ou cancele
     na barra do topo."

E respondeu: *"não mostra barra no topo só para constar"*. Ele estava certo.
Depois de recarregar a página, a aba não guarda nenhuma lembrança do
processamento — quem sabe dele é o servidor, e o servidor mandava quatro
palavras. A única saída oferecida era um botão que não existia na tela.

O corpo do 409 passa a carregar o que só o servidor sabe: qual operação está
rodando, com qual job, e há quanto tempo. Com isso a página remonta a barra e o
botão de cancelar volta a existir de verdade.
"""

from datetime import datetime, timedelta

import pytest

import app as aplicacao


@pytest.fixture
def em_andamento():
    """Deixa o servidor ocupado e devolve tudo como estava depois."""
    anterior = dict(aplicacao.current_task)
    aplicacao.current_task["active"] = True
    aplicacao.current_task["operation"] = "cut"
    aplicacao.current_task["job_id"] = "job-abc"
    aplicacao.current_task["started_at"] = (
        datetime.now() - timedelta(seconds=125)
    ).isoformat(timespec="seconds")
    yield
    aplicacao.current_task.clear()
    aplicacao.current_task.update(anterior)


def test_a_recusa_diz_o_que_esta_rodando(em_andamento):
    with aplicacao.app.test_request_context():
        resposta, codigo = aplicacao._busy_response()
    corpo = resposta.get_json()

    assert codigo == 409
    assert corpo["busy"] is True
    assert corpo["operation"] == "cut"
    assert corpo["job_id"] == "job-abc"
    assert 120 <= corpo["elapsed_seconds"] <= 135, (
        "sem o tempo decorrido a página não tem como mostrar o relógio da barra"
    )


def test_a_recusa_sobrevive_a_um_inicio_sem_registro():
    """`started_at` pode estar vazio ou corrompido; isso não pode virar erro 500."""
    anterior = dict(aplicacao.current_task)
    try:
        for valor in (None, "", "ontem de manhã"):
            aplicacao.current_task["active"] = True
            aplicacao.current_task["operation"] = ""
            aplicacao.current_task["job_id"] = None
            aplicacao.current_task["started_at"] = valor
            with aplicacao.app.test_request_context():
                resposta, codigo = aplicacao._busy_response()
            corpo = resposta.get_json()
            assert codigo == 409
            assert corpo["elapsed_seconds"] is None
            assert corpo["busy"] is True
    finally:
        aplicacao.current_task.clear()
        aplicacao.current_task.update(anterior)


def test_o_texto_da_tela_nao_manda_mais_procurar_uma_barra_que_nao_existe():
    """O controle: a frase antiga não pode voltar sozinha numa edição futura.

    Ela só era verdadeira se a barra já estivesse na tela — que é exatamente o
    caso em que o editor não precisaria da mensagem.
    """
    from pathlib import Path

    tela = Path(__file__).resolve().parents[1] / "static" / "js" / "mesa-app.js"
    texto = tela.read_text(encoding="utf-8")

    assert "adotarProcessamentoDoServidor" in texto, (
        "a página voltou a recusar o 409 sem remontar a barra"
    )
    assert "Espere ele terminar ou cancele na barra do topo" not in texto
