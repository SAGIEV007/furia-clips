"""Duas ações ao mesmo tempo, que era o que o editor descrevia como bug.

Quatro rotas checavam o sinalizador global de "já tem coisa rodando" fora de
qualquer trava, e uma delas — a remoção de silêncio — só ligava o sinalizador
lá dentro da thread, depois de a rota já ter respondido. A checagem era inútil
por construção: duas requisições seguidas passavam as duas.

Pior que isso: o bloco `finally` de cada uma zerava o sinalizador global. Uma
tarefa curta terminando desligava a guarda de outra tarefa longa ainda em
andamento, e a partir dali qualquer botão iniciava trabalho concorrente sobre os
mesmos arquivos.
"""

import re
from pathlib import Path

FONTE = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")


def _rotas_que_iniciam_tarefa():
    linhas = FONTE.split("\n")
    rota, inicio, achadas = None, 0, []
    for numero, linha in enumerate(linhas, start=1):
        marca = re.match(r'@app\.route\("([^"]+)"', linha)
        if marca:
            rota, inicio = marca.group(1), numero
        if "threading.Thread(target=task" in linha and rota:
            achadas.append((rota, "\n".join(linhas[inicio - 1:numero])))
    return achadas


def test_toda_rota_que_inicia_tarefa_usa_a_trava():
    for rota, trecho in _rotas_que_iniciam_tarefa():
        assert "processing_lock" in trecho, f"{rota} inicia trabalho sem a trava"


def test_a_marcacao_acontece_dentro_da_trava():
    """Checar e marcar têm de ser um passo só, senão a checagem não vale nada."""
    for rota, trecho in _rotas_que_iniciam_tarefa():
        guarda = re.search(
            r"with processing_lock:\s*\n\s*if current_task\[\"active\"\]:\s*\n"
            r".*?\n\s*_set_legacy_task\(",
            trecho,
            re.DOTALL,
        )
        assert guarda, f"{rota} não marca a tarefa dentro da mesma trava em que checa"


def test_ninguem_mexe_no_sinalizador_cru():
    """Zerar o sinalizador direto desligava a guarda de outra tarefa."""
    assert 'current_task["active"] = False' not in FONTE
    assert 'current_task["active"] = True' not in FONTE


def test_encontrou_as_rotas_esperadas():
    """Guarda do próprio teste: se o padrão parar de casar, ele não pode passar vazio."""
    rotas = [rota for rota, _ in _rotas_que_iniciam_tarefa()]

    assert len(rotas) >= 6
    assert "/api/process/silence" in rotas
