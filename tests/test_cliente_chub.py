"""O cliente do CHUB, exercitado contra um servidor de mentira que responde de verdade.

O servidor real do Acervo está atrás de uma política de rede que o ambiente onde
este código foi escrito não atravessa, e por isso nada aqui prova que a conexão
com ele funciona. O que estes testes provam é a outra metade, que é a que
costuma quebrar: o formato do pedido, a leitura das duas formas de resposta que
o protocolo admite, a paginação, e o que acontece quando o servidor recusa.

Um servidor falso vale como teste porque o protocolo é escrito, não adivinhado.
Ele responde com as mesmas cascas do MCP e com a mesma forma de página que o
Acervo documenta, então um cliente que passe aqui e falhe lá falhou por causa da
rede ou de uma diferença do servidor real — e as duas coisas aparecem na primeira
tentativa do operador, com mensagem, em vez de silenciosamente.
"""

import json

import pytest

from modules.chub_client import ChubClient, ChubError, videos_do_acervo


class RespostaFalsa:
    def __init__(self, corpo, *, status=200, headers=None):
        self._corpo = corpo
        self.status_code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = corpo if isinstance(corpo, str) else json.dumps(corpo)
        self.content = self.text.encode("utf-8")

    def json(self):
        return json.loads(self.text)


class ServidorFalso:
    """Um MCP mínimo: apresenta-se, aceita `tools/call`, e conta as chamadas."""

    def __init__(self, respostas=None, *, fluxo=False, status=200):
        self.respostas = respostas or {}
        self.fluxo = fluxo
        self.status = status
        self.pedidos = []

    def post(self, url, json=None, headers=None, timeout=None):
        corpo = json or {}
        self.pedidos.append((corpo.get("method"), corpo.get("params"), headers))
        metodo = corpo.get("method")

        if self.status >= 400:
            return RespostaFalsa("recusado", status=self.status)
        if metodo == "initialize":
            return self._envelope(corpo, {"protocolVersion": "2025-06-18"},
                                  headers={"Content-Type": "application/json",
                                           "Mcp-Session-Id": "sessao-123"})
        if metodo == "notifications/initialized":
            return RespostaFalsa("", status=202)
        if metodo == "tools/call":
            nome = (corpo.get("params") or {}).get("name")
            argumentos = (corpo.get("params") or {}).get("arguments") or {}
            valor = self.respostas.get(nome)
            if callable(valor):
                valor = valor(argumentos)
            resultado = {"content": [{"type": "text", "text": _json.dumps(valor)}]}
            return self._envelope(corpo, resultado)
        return self._envelope(corpo, {})

    def _envelope(self, pedido, resultado, headers=None):
        envelope = {"jsonrpc": "2.0", "id": pedido.get("id"), "result": resultado}
        if not self.fluxo:
            return RespostaFalsa(envelope, headers=headers)
        # A outra forma que o protocolo admite: um fluxo de eventos, com ruído
        # de progresso antes do resultado.
        linhas = [
            "event: message",
            "data: " + _json.dumps({"jsonrpc": "2.0", "method": "notifications/progress"}),
            "",
            "data: " + _json.dumps(envelope),
            "",
        ]
        cabecalhos = dict(headers or {})
        cabecalhos["Content-Type"] = "text/event-stream"
        return RespostaFalsa("\n".join(linhas), headers=cabecalhos)


import json as _json  # noqa: E402  (o servidor falso acima sombreia o nome `json`)

URL = "https://exemplo.invalido/mcp/wk_teste"


def test_a_credencial_nunca_e_inventada(monkeypatch):
    """Sem endereço configurado o cliente para, em vez de tentar um padrão."""
    import os
    from pathlib import Path

    import modules.chub_client as _cc
    monkeypatch.setattr(_cc, "endpoint_configurado", lambda *a, **k: "")

    anterior = os.environ.pop("FURIA_CHUB_MCP_URL", None)
    try:
        with pytest.raises(ChubError) as erro:
            ChubClient()
        assert "FURIA_CHUB_MCP_URL" in str(erro.value)
    finally:
        if anterior is not None:
            os.environ["FURIA_CHUB_MCP_URL"] = anterior


def test_a_apresentacao_acontece_uma_vez_so():
    """`initialize` é caro e vale pela sessão inteira."""
    servidor = ServidorFalso({"chub_acervo_stats": {"ok": True}})
    cliente = ChubClient(URL, session=servidor)
    cliente.chamar_ferramenta("chub_acervo_stats")
    cliente.chamar_ferramenta("chub_acervo_stats")
    metodos = [metodo for metodo, _, _ in servidor.pedidos]
    assert metodos.count("initialize") == 1, metodos
    assert metodos.count("notifications/initialized") == 1, metodos


def test_a_sessao_devolvida_pelo_servidor_volta_em_todo_pedido():
    """É o que permite ao servidor paginar sem refazer trabalho."""
    servidor = ServidorFalso({"chub_acervo_stats": {"ok": True}})
    cliente = ChubClient(URL, session=servidor)
    cliente.chamar_ferramenta("chub_acervo_stats")
    _, _, cabecalhos = servidor.pedidos[-1]
    assert cabecalhos.get("Mcp-Session-Id") == "sessao-123"


def test_a_casca_do_mcp_sai_e_o_json_de_dentro_fica():
    servidor = ServidorFalso({"chub_acervo_stats": {"groups": [{"videos": 3}]}})
    resultado = ChubClient(URL, session=servidor).chamar_ferramenta("chub_acervo_stats")
    assert resultado == {"groups": [{"videos": 3}]}


def test_a_resposta_em_fluxo_de_eventos_e_lida_igual():
    """Metade dos servidores MCP responde assim, e o resultado tem que ser o mesmo."""
    servidor = ServidorFalso({"chub_acervo_stats": {"groups": []}}, fluxo=True)
    resultado = ChubClient(URL, session=servidor).chamar_ferramenta("chub_acervo_stats")
    assert resultado == {"groups": []}


def test_credencial_recusada_diz_que_e_a_credencial():
    """403 num endereço que carrega a chave no caminho tem uma causa provável."""
    cliente = ChubClient(URL, session=ServidorFalso(status=403))
    with pytest.raises(ChubError) as erro:
        cliente.chamar_ferramenta("chub_acervo_stats")
    assert "credencial" in str(erro.value).lower()


def test_erro_do_protocolo_chega_com_o_motivo_do_servidor():
    class Recusa(ServidorFalso):
        def _envelope(self, pedido, resultado, headers=None):
            if pedido.get("method") != "tools/call":
                return super()._envelope(pedido, resultado, headers)
            return RespostaFalsa({
                "jsonrpc": "2.0", "id": pedido.get("id"),
                "error": {"code": -32602, "message": "videoId desconhecido"},
            })

    cliente = ChubClient(URL, session=Recusa())
    with pytest.raises(ChubError) as erro:
        cliente.chamar_ferramenta("chub_acervo_blocks", {"videoId": "xxx"})
    assert "videoId desconhecido" in str(erro.value)


# ── paginação: parar cedo é perder metade do Acervo em silêncio ────────────

def test_a_transcricao_junta_todas_as_paginas():
    """Um vídeo de uma hora não cabe numa página, e parar na primeira não avisa."""
    def responder(argumentos):
        inicio = int(argumentos.get("startSentenceIdx") or 0)
        if inicio >= 10:
            return {"sentences": [{"idx": 10, "text": "fim"}], "page": {"nextSentenceIdx": None}}
        return {
            "sentences": [{"idx": i, "text": f"frase {i}"} for i in range(inicio, inicio + 5)],
            "page": {"nextSentenceIdx": inicio + 5},
        }

    cliente = ChubClient(URL, session=ServidorFalso({"chub_acervo_transcript": responder}))
    resultado = cliente.transcricao("KpjvWf9SsWQ")
    assert [s["idx"] for s in resultado["sentences"]] == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_os_blocos_juntam_todas_as_paginas():
    def responder(argumentos):
        if argumentos.get("cursor") == "p2":
            return {"items": [{"id": "c"}], "nextCursor": None}
        if argumentos.get("cursor") == "p1":
            return {"items": [{"id": "b"}], "nextCursor": "p2"}
        return {"items": [{"id": "a"}], "nextCursor": "p1"}

    cliente = ChubClient(URL, session=ServidorFalso({"chub_acervo_blocks": responder}))
    resultado = cliente.blocos("KpjvWf9SsWQ")
    assert [item["id"] for item in resultado["items"]] == ["a", "b", "c"]
    assert "nextCursor" not in resultado


def test_um_servidor_que_nunca_termina_nao_prende_o_processo():
    """"Tem mais" para sempre é um jeito de o processo nunca voltar."""
    cliente = ChubClient(URL, session=ServidorFalso({
        "chub_acervo_blocks": lambda a: {"items": [{"id": "x"}], "nextCursor": "sempre"},
    }))
    resultado = cliente.blocos("KpjvWf9SsWQ")
    assert len(resultado["items"]) < 1000


def test_listar_video_nao_repete_o_mesmo_video():
    """Um vídeo com trinta blocos é um vídeo, não trinta."""
    def responder(argumentos):
        if argumentos.get("cursor"):
            return {"items": [], "nextCursor": None}
        video = {"youtubeId": "KpjvWf9SsWQ", "title": "João Pessoa"}
        outro = {"youtubeId": "fZpyzDpnA2o", "title": "Podcast"}
        return {
            "items": [{"video": video}, {"video": video}, {"video": outro}],
            "nextCursor": None,
        }

    cliente = ChubClient(URL, session=ServidorFalso({"chub_acervo_blocks": responder}))
    ids = [video["youtubeId"] for video in videos_do_acervo(cliente)]
    assert ids == ["KpjvWf9SsWQ", "fZpyzDpnA2o"]


# ── a chave mora na URL, e erro de rede repete a URL ───────────────────────

def test_a_chave_nao_sai_na_mensagem_de_erro():
    """A primeira falha real deste cliente imprimiu a credencial inteira.

    O endereço do CHUB é uma senha escrita como link: quem tiver o `wk_...` tem
    o Acervo. E toda mensagem de erro de rede repete a URL que falhou, então o
    caminho mais provável de a chave vazar não é um arquivo commitado — é um
    operador colando o erro num chat para pedir ajuda.
    """
    import requests

    from modules.chub_client import ocultar_credencial

    # Chave inventada, com a mesma forma da real. Uma credencial de verdade
    # dentro de um teste é a credencial commitada — que é o defeito que este
    # próprio teste existe para impedir.
    chave = "wk_0000exemploFALSAnaoEhChaveDeNinguem0000"

    class Explode:
        def post(self, *args, **kwargs):
            raise requests.ConnectionError(
                f"Max retries exceeded with url: /mcp/{chave} (Caused by ...)"
            )

    cliente = ChubClient(f"https://exemplo.invalido/mcp/{chave}", session=Explode())
    with pytest.raises(ChubError) as erro:
        cliente.chamar_ferramenta("chub_acervo_stats")

    assert chave not in str(erro.value), "a credencial saiu inteira na mensagem"
    assert "wk_…" in str(erro.value), str(erro.value)
    # E o mascaramento não pode comer o resto da mensagem, que é o diagnóstico.
    assert "Max retries" in str(erro.value)

    # Vale para qualquer texto, inclusive corpo de resposta do servidor.
    assert chave not in ocultar_credencial(f"erro no {chave} agora")


def test_o_corpo_de_erro_do_servidor_tambem_e_limpo():
    class Vaza(ServidorFalso):
        def post(self, url, json=None, headers=None, timeout=None):
            self.pedidos.append((("post",), None, headers))
            return RespostaFalsa(
                "falha ao processar /mcp/wk_0000exemploFALSAnaoEhChaveDeNinguem0000",
                status=500,
            )

    cliente = ChubClient("https://exemplo.invalido/mcp/wk_x", session=Vaza())
    with pytest.raises(ChubError) as erro:
        cliente.chamar_ferramenta("chub_acervo_stats")
    assert "wk_0000exemplo" not in str(erro.value), str(erro.value)


# ── onde o endereço fica guardado ─────────────────────────────────────────

def test_o_endereco_e_lido_do_arquivo_local(tmp_path, monkeypatch):
    """O `chub.bat` grava uma vez e o app passa a saber, sem configurar duas vezes."""
    from modules.chub_client import arquivo_do_endpoint, endpoint_configurado

    monkeypatch.delenv("FURIA_CHUB_MCP_URL", raising=False)
    arquivo = arquivo_do_endpoint(tmp_path)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    # O `echo` do Windows deixa quebra de linha, e uma URL com "\n" no fim falha
    # de um jeito que não parece com a causa.
    arquivo.write_text("https://exemplo.invalido/mcp/wk_gravado\r\n", encoding="utf-8")

    assert endpoint_configurado(data_dir=tmp_path) == "https://exemplo.invalido/mcp/wk_gravado"


def test_o_ambiente_ganha_do_arquivo(tmp_path, monkeypatch):
    """Uma corrida pontual precisa poder apontar para outro lugar."""
    from modules.chub_client import arquivo_do_endpoint, endpoint_configurado

    arquivo = arquivo_do_endpoint(tmp_path)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text("https://exemplo.invalido/mcp/wk_arquivo", encoding="utf-8")
    monkeypatch.setenv("FURIA_CHUB_MCP_URL", "https://exemplo.invalido/mcp/wk_ambiente")

    assert endpoint_configurado(data_dir=tmp_path).endswith("wk_ambiente")


def test_o_arquivo_do_endereco_fica_fora_do_repositorio():
    """Este repositório é público; o endereço é a senha."""
    from pathlib import Path

    from modules.chub_client import arquivo_do_endpoint

    repositorio = Path(__file__).resolve().parents[1]
    assert repositorio not in arquivo_do_endpoint().parents
