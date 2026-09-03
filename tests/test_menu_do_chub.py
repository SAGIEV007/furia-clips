"""O CHUB tem que ser alcançável sem terminal.

O editor perguntou, depois de conectar com sucesso: "como eu rodo esse
chub.bat --espelho???" — e a pergunta estava certa. Passar argumento para um
arquivo .bat exige abrir um terminal e digitar o caminho, e ninguém deveria
precisar disso para ver o que o próprio programa já sabe.

Dois defeitos de projeto, os dois deste tamanho:

O `chub.bat` clicado duas vezes só sabia testar a conexão. Todo o resto —
espelho, lista, download, vínculo — existia e era inalcançável para quem não
abre terminal, que é exatamente a pessoa para quem o arquivo foi feito.

E o `--espelho` pedia o endereço do CHUB antes de rodar. O espelho vem dentro do
programa e não fala com servidor nenhum; exigir a credencial para lê-lo é cobrar
senha para abrir uma porta que já está aberta.
"""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CHUB_BAT = RAIZ / "chub.bat"


def texto() -> str:
    return CHUB_BAT.read_text(encoding="utf-8", errors="replace")


def test_o_menu_oferece_tudo_o_que_o_script_faz():
    """Cada função do sincronizador precisa ter um número no menu."""
    conteudo = texto()
    assert ":menu" in conteudo, "o clique duplo voltou a não ter menu"
    for opcao in ("--espelho", "--testar", "--listar", "--tudo", "--vincular"):
        assert opcao in conteudo, f"{opcao} ficou inalcançável pelo menu"
    for numero in range(7):
        assert f'"{numero}"' in conteudo, f"falta a opção [{numero}]"


def test_o_espelho_nao_pede_credencial():
    """Ele é lido de um arquivo local; pedir o endereço seria cobrar à toa.

    A ordem no arquivo é o que garante isso: o desvio para `:executar` tem que
    vir ANTES do trecho que pergunta o endereço.
    """
    conteudo = texto()
    desvio = conteudo.find('if /i "%~1"=="--espelho" goto :executar')
    pergunta = conteudo.find("Cole o endereco do CHUB")
    assert desvio > 0, "o atalho do espelho sumiu"
    assert desvio < pergunta, "o espelho voltou a pedir a credencial antes de rodar"


def test_o_espelho_roda_de_verdade_sem_endereco_no_ambiente():
    """A prova de que o atalho acima não é só uma linha bonita no .bat."""
    resultado = subprocess.run(
        [sys.executable, "scripts/sincronizar_acervo.py", "--espelho"],
        cwd=RAIZ, capture_output=True, text=True,
        env={**os.environ, "HOME": str(Path.home()), "USERPROFILE": str(Path.home()), "PYTHONIOENCODING": "utf-8"},
    )
    assert resultado.returncode == 0, resultado.stderr[:400]
    assert "medições de gancho" in resultado.stdout
    assert "news-peg" in resultado.stdout


def test_a_chave_nunca_e_escrita_na_pasta_do_programa():
    """O repositório é público. O endereço carrega a credencial dentro dele."""
    conteudo = texto()
    assert "%USERPROFILE%\\FuriaClipsData" in conteudo
    assert "wk_a0" not in conteudo and "wk_" not in conteudo.replace('wk_..."', "").replace("wk_...", "")


def test_quem_prefere_terminal_continua_podendo():
    """O menu é uma porta a mais, não uma porta no lugar da outra."""
    conteudo = texto()
    assert 'if not "%~1"=="" goto :executar' in conteudo
    assert "%*" in conteudo, "os argumentos do terminal deixaram de ser repassados"


def test_o_menu_volta_para_si_mesmo_depois_de_cada_acao():
    """Fechar a janela a cada consulta obrigaria a reabrir e reescolher."""
    conteudo = texto()
    depois = conteudo[conteudo.find(":executar"):]
    assert "goto :menu" in depois, "depois de rodar, o menu não volta"
