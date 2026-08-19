"""A classe de defeito que quebra em execução não pode voltar.

O editor cobrou, com razão: eu vinha achando bugs um a um em varredura
direcionada, sem nunca passar por todas as linhas. Passei — com ruff, sobre os
25 mil e poucos que existem — e a auditoria achou um NameError garantido no
"Executar Tudo": o processo completo lia o sinalizador de facetracking em lugar
nenhum e mesmo assim o usava na decisão de reenquadrar.

Este teste transforma aquela auditoria em rotina. Não cobre estilo: cobre
exatamente as regras cuja violação é uma falha de execução ou uma perda
silenciosa de dado.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# F821 nome indefinido, F811 redefinição que apaga a anterior, F601/B033 chave ou
# valor duplicado em literal, F632 comparação de literal com `is`, E9 erro de
# sintaxe ou de indentação.
REGRAS = "F821,F811,F601,B033,F632,E9"


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff não instalado neste ambiente")
def test_nenhum_defeito_de_execucao_no_projeto():
    resultado = subprocess.run(
        ["ruff", "check", "--select", REGRAS, "--output-format", "concise", "."],
        cwd=RAIZ, capture_output=True, text=True,
    )

    assert resultado.returncode == 0, f"defeitos de execução encontrados:\n{resultado.stdout}"
