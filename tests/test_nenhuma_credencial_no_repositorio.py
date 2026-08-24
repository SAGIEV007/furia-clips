"""Nenhum arquivo do projeto pode carregar uma credencial.

Este teste existe porque a regra falhou. A chave do Campaign Hub — um endereço
que carrega o segredo no próprio caminho, `/mcp/wk_...` — ficou escrita em três
documentos de continuidade e foi commitada num repositório **público**, onde
qualquer pessoa podia lê-la. Ela dá leitura do Acervo inteiro: 522 vídeos, 825
horas de material, mais as métricas das contas e a base da Missão.

Ninguém colou a chave ali por descuido de digitação. Ela entrou como
documentação — "Campaign Hub MCP autorizado", com o link ao lado, para a próxima
sessão saber onde ele estava. É assim que credencial vaza na prática: alguém
sendo prestativo.

Um teste é o único lugar onde essa regra sobrevive a mudar de sessão, de branch
e de pessoa.
"""

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Formas de segredo que este projeto de fato manipula. A ideia não é achar todo
# segredo possível — é travar os que já apareceram e os vizinhos óbvios.
PADROES = (
    ("chave do Campaign Hub", re.compile(r"\bwk_[A-Za-z0-9]{24,}\b")),
    ("chave de API do Google/Gemini", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("chave da Anthropic", re.compile(r"\bsk-ant-[0-9A-Za-z_-]{20,}\b")),
    ("token do GitHub", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}\b")),
)

# O que o teste declara como exemplo tem a forma de segredo de propósito.
PERMITIDO = {"tests/test_nenhuma_credencial_no_repositorio.py", "tests/test_cliente_chub.py"}


def _arquivos_versionados():
    saida = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout
    return [linha for linha in saida.splitlines() if linha.strip()]


def test_nenhum_arquivo_versionado_carrega_credencial():
    achados = []
    for relativo in _arquivos_versionados():
        if relativo in PERMITIDO:
            continue
        caminho = RAIZ / relativo
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binário ou ilegível: não é onde uma chave é escrita
        for nome, padrao in PADROES:
            achado = padrao.search(texto)
            if achado:
                achados.append(f"{relativo}: {nome} ({achado.group()[:12]}…)")

    assert not achados, (
        "credencial em arquivo versionado — este repositório é público:\n  "
        + "\n  ".join(achados)
        + "\n\nTire do arquivo E peça a rotação da chave: apagar não desfaz o "
          "que já foi publicado, porque o histórico do git guarda."
    )


def test_o_exemplo_do_teste_do_cliente_e_mesmo_falso():
    """O controle: o teste acima só pode liberar quem não tem segredo de verdade.

    A chave de exemplo em `test_cliente_chub.py` é inventada e precisa continuar
    sendo — foi ali que a chave real do operador entrou uma vez.
    """
    texto = (RAIZ / "tests" / "test_cliente_chub.py").read_text(encoding="utf-8")
    for achado in PADROES[0][1].findall(texto):
        assert "exemplo" in achado.lower() or "falsa" in achado.lower(), (
            f"a chave {achado[:12]}… no teste do cliente não se declara falsa"
        )
