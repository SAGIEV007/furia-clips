"""Regressão do bootstrap do modelo facial com caminho não-ASCII.

Bug real reportado em 31/08 pelo log de produção do usuário:

    [Face Model] Não foi possível preparar o modelo facial:
    Caracteres inválidos no caminho.

Causa: `run.bat` chama o script PowerShell com `-ProjectRoot "%~dp0"`. Quando a
pasta do projeto tem caracteres não-ASCII (o usuário roda de
`C:\\Users\\nandi\\OneDrive\\Área de Trabalho\\...`), o cmd.exe entrega o
argumento no code page OEM e o PowerShell recebe "Área" como "µrea". O caminho
corrompido não existe, o script abortava, o modelo nunca era baixado — e sem
modelo facial `plan_layout` devolve family=unknown, o reframe 9:16 é bloqueado e
TODOS os cortes saem em 16:9, inúteis para Instagram.

Correção: o script ignora `-ProjectRoot` quando ele aponta para um caminho
inexistente e cai em `$PSScriptRoot`, que é resolvido pelo próprio PowerShell e
portanto imune à corrupção de code page.
"""

import os
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "ensure_face_model.ps1")
MODEL_RELATIVE = os.path.join("models", "blaze_face_short_range.tflite")
EXPECTED_SHA256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"

windows_only = pytest.mark.skipif(
    sys.platform != "win32", reason="bootstrap do modelo facial é específico do Windows"
)


def _powershell():
    return shutil.which("powershell.exe") or shutil.which("pwsh")


def test_script_nao_usa_projectroot_como_default_do_parametro():
    """O default do parâmetro não pode mais ser calculado inline.

    Antes: `[string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)`. Isso
    parece seguro, mas o default só vale quando o argumento está AUSENTE — e o
    run.bat sempre passa um argumento, que pode vir corrompido. A blindagem tem
    de ser uma validação explícita no corpo do script.
    """
    source = open(SCRIPT, encoding="utf-8-sig").read()

    assert "[string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)" not in source, (
        "o default inline não protege contra argumento corrompido vindo do .bat"
    )
    assert "Test-Path -LiteralPath $ProjectRoot" in source, (
        "o script precisa validar que ProjectRoot existe antes de confiar nele"
    )


@windows_only
@pytest.mark.skipif(_powershell() is None, reason="PowerShell indisponível")
def test_baixa_modelo_mesmo_com_projectroot_corrompido(tmp_path):
    """Reproduz o cenário exato do log: caminho com acento corrompido.

    O script deve ignorar o argumento inválido, usar $PSScriptRoot e ainda
    assim entregar o modelo íntegro.
    """
    projeto = tmp_path / "furia-fake"
    (projeto / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, projeto / "scripts" / "ensure_face_model.ps1")

    # Exatamente a corrupção observada: "Área" -> "µrea".
    corrompido = "C:\\Users\\nandi\\OneDrive\\\u00b5rea de Trabalho\\furia\\"

    resultado = subprocess.run(
        [
            _powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(projeto / "scripts" / "ensure_face_model.ps1"),
            "-ProjectRoot", corrompido,
        ],
        capture_output=True,
        timeout=600,
    )
    saida = resultado.stdout.decode("cp1252", errors="replace")

    assert "Caracteres inválidos no caminho" not in saida, (
        f"a regressão do caminho não-ASCII voltou. Saída: {saida}"
    )

    destino = projeto / MODEL_RELATIVE
    if not destino.exists():
        pytest.skip("download indisponível neste ambiente (offline)")

    assert destino.stat().st_size == 229746, "tamanho do modelo não confere"

    import hashlib

    digest = hashlib.sha256(destino.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256, "SHA-256 do modelo baixado não confere"
