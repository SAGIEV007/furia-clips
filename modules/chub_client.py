"""Falar com o Campaign Hub direto, em vez de esperar um arquivo que alguém traz.

O `acervo_library` já sabia ler blocos do Acervo — de um arquivo numa pasta, que
um humano tinha que produzir. A documentação dele registrava o resultado disso:
o caminho "ficou vazio e toda rodada lia ``bloco_chub: null`` mesmo para fontes
com quatorze blocos publicados". Encanamento pronto, sem água.

Este módulo é a torneira. O CHUB expõe um servidor MCP sobre HTTP, e MCP é um
protocolo comum: uma sequência de chamadas JSON-RPC. Não é preciso um cliente
especial nem uma biblioteca nova, e é por isso que aqui só entra `requests`, que
o projeto já usa.

Duas coisas que este arquivo deliberadamente não faz:

**Não guarda o endereço.** A URL do CHUB carrega a credencial no próprio caminho
(``/mcp/wk_...``), então ela é uma senha escrita como link. Ela entra por
`FURIA_CHUB_MCP_URL` ou pelas configurações locais do operador, e não pode ser
escrita em nenhum arquivo versionado. Quem tiver o link tem o Acervo inteiro.

**Não decide nada de editorial.** Ele busca, pagina e devolve a resposta do
servidor como veio. Converter em export é do `acervo_library`, e escolher o corte
é do `clip_selector`. Cliente que interpreta é cliente que mente quando o
servidor muda.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterator

import requests


DEFAULT_TIMEOUT_S = 120
PROTOCOL_VERSION = "2025-06-18"

# O Acervo pagina em duas moedas diferentes: a tabela de frases anda por índice
# de frase e os blocos por cursor opaco. Um limite alto economiza viagem, mas o
# servidor tem o direito de devolver menos — quem manda no fim da página é a
# resposta, nunca o pedido.
SENTENCE_PAGE = 5000
BLOCK_PAGE = 500

# Um vídeo de duas horas de live tem milhares de frases. O teto existe para que
# um servidor que responda sempre "tem mais" não prenda o processo para sempre.
MAX_PAGES = 200


class ChubError(RuntimeError):
    """Falha ao falar com o CHUB, com o motivo que o servidor deu."""


# A chave mora no caminho da URL, e mensagem de erro de rede repete a URL. A
# primeira vez que este cliente falhou contra um endereço inexistente ele
# imprimiu "Max retries exceeded with url: /mcp/wk_x" — ou seja, a credencial
# inteira, no console e em qualquer log que o operador guarde ou mande para
# alguém. Um erro não pode ser o jeito de a senha sair.
_SEGREDO = re.compile(r"(wk_)[A-Za-z0-9_-]{4,}")


def ocultar_credencial(texto: Any) -> str:
    """Trocar a chave por um resto reconhecível, em qualquer texto de saída."""
    return _SEGREDO.sub(lambda achado: achado.group(1) + "…", str(texto))


def arquivo_do_endpoint(data_dir=None):
    """Onde o endereço fica guardado, fora do repositório.

    `FuriaClipsData` é a pasta local do operador, ao lado do resto do que o app
    grava por lá. Nunca dentro do checkout: esta pasta vai para o GitHub, e o
    repositório é público.
    """
    from pathlib import Path

    base = Path(
        data_dir
        or os.environ.get("FURIA_CLIPS_DATA_DIR")
        or (Path.home() / "FuriaClipsData")
    )
    return base / "chub-endpoint.txt"


def endpoint_configurado(settings: dict | None = None, *, data_dir=None) -> str:
    """O endereço do CHUB, de onde o operador o tiver posto.

    A ordem é a de quem manda mais: o ambiente do processo primeiro, porque é
    ele que um script de sincronização define para uma corrida só; as
    configurações do app depois; e por último o arquivo que o `chub.bat` grava
    na primeira vez — que é como o app passa a saber o endereço sem ninguém
    configurar nada duas vezes.
    """
    candidatos = [
        os.environ.get("FURIA_CHUB_MCP_URL"),
        (settings or {}).get("chub_mcp_url"),
    ]
    try:
        arquivo = arquivo_do_endpoint(data_dir)
        if arquivo.is_file():
            candidatos.append(arquivo.read_text(encoding="utf-8"))
    except OSError:
        pass
    for valor in candidatos:
        # Um arquivo escrito pelo `echo` do Windows chega com quebra de linha, e
        # uma URL com "\n" no fim falha de um jeito que não parece com a causa.
        if str(valor or "").strip():
            return str(valor).strip()
    return ""


def _texto_do_resultado(payload: Any) -> Any:
    """Desembrulhar o conteúdo de um resultado de ferramenta MCP.

    Uma ferramenta MCP responde numa casca — ``content: [{type, text}]`` — e o
    que interessa é o JSON dentro do texto. Servidores também podem devolver
    ``structuredContent`` já decodificado, e aí não há o que desembrulhar.
    """
    if not isinstance(payload, dict):
        return payload
    if isinstance(payload.get("structuredContent"), dict):
        return payload["structuredContent"]
    partes = []
    for item in payload.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            partes.append(str(item.get("text") or ""))
    texto = "".join(partes).strip()
    if not texto:
        return payload
    try:
        return json.loads(texto)
    except ValueError:
        return {"text": texto}


def _resposta_json(resposta: requests.Response) -> dict:
    """Ler a resposta, seja ela JSON puro ou um fluxo de eventos.

    O transporte HTTP do MCP deixa o servidor escolher: ou devolve
    ``application/json`` de uma vez, ou abre um ``text/event-stream`` e manda o
    resultado numa linha ``data:``. Um cliente que só entenda a primeira forma
    funciona contra metade dos servidores e falha contra a outra metade sem dizer
    por quê.
    """
    tipo = (resposta.headers.get("Content-Type") or "").lower()
    if "text/event-stream" not in tipo:
        return resposta.json()
    ultimo = None
    for linha in resposta.text.splitlines():
        if not linha.startswith("data:"):
            continue
        corpo = linha[5:].strip()
        if not corpo or corpo == "[DONE]":
            continue
        try:
            evento = json.loads(corpo)
        except ValueError:
            continue
        # O fluxo pode carregar notificações de progresso antes do resultado; o
        # que fecha a chamada é o envelope que traz `result` ou `error`.
        if isinstance(evento, dict) and ("result" in evento or "error" in evento):
            ultimo = evento
    if ultimo is None:
        raise ChubError("o servidor abriu um fluxo de eventos e não mandou resultado")
    return ultimo


class ChubClient:
    """Uma sessão MCP contra o Campaign Hub.

    O ciclo de vida do protocolo é curto: apresenta-se, avisa que está pronto e
    aí pode chamar ferramenta. A sessão vale enquanto o objeto viver, e o
    servidor pode devolver um identificador que precisa voltar em todo pedido
    seguinte — é o que permite a ele paginar sem repetir trabalho.
    """

    def __init__(self, url: str = "", *, timeout: int = DEFAULT_TIMEOUT_S, session=None):
        self.url = (url or endpoint_configurado()).strip()
        if not self.url:
            raise ChubError(
                "endereço do CHUB não configurado: defina FURIA_CHUB_MCP_URL ou "
                "'chub_mcp_url' nas configurações"
            )
        self.timeout = timeout
        self._http = session or requests.Session()
        self._id = 0
        self._session_id = ""
        self._pronto = False

    # ── protocolo ────────────────────────────────────────────────────────────

    def _chamar(self, metodo: str, params: dict | None = None, *, notificacao: bool = False) -> Any:
        corpo: dict[str, Any] = {"jsonrpc": "2.0", "method": metodo}
        if params is not None:
            corpo["params"] = params
        if not notificacao:
            self._id += 1
            corpo["id"] = self._id

        cabecalhos = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            cabecalhos["Mcp-Session-Id"] = self._session_id

        try:
            resposta = self._http.post(
                self.url, json=corpo, headers=cabecalhos, timeout=self.timeout
            )
        except requests.RequestException as erro:
            raise ChubError(
                f"não consegui falar com o CHUB: {ocultar_credencial(erro)}"
            ) from erro

        # O identificador de sessão vem na resposta do `initialize` e vale para
        # todas as chamadas seguintes.
        novo = resposta.headers.get("Mcp-Session-Id") or resposta.headers.get("mcp-session-id")
        if novo:
            self._session_id = novo

        if resposta.status_code in (401, 403):
            raise ChubError(
                f"o CHUB recusou a credencial ({resposta.status_code}). A URL carrega a "
                f"chave no caminho — confira se ela está inteira e ainda é válida."
            )
        if resposta.status_code >= 400:
            raise ChubError(
                f"o CHUB respondeu {resposta.status_code}: "
                f"{ocultar_credencial(resposta.text[:300])}"
            )
        # Uma notificação não tem resposta para ler.
        if notificacao or not (resposta.content or b"").strip():
            return None

        envelope = _resposta_json(resposta)
        if isinstance(envelope, dict) and envelope.get("error"):
            erro = envelope["error"]
            raise ChubError(
                f"o CHUB recusou {metodo}: {erro.get('message') or erro} "
                f"(código {erro.get('code')})"
            )
        return (envelope or {}).get("result")

    def conectar(self) -> dict:
        """Apresentar-se e avisar que está pronto. Idempotente."""
        if self._pronto:
            return {}
        resultado = self._chamar("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "furia-clips", "version": "6.37"},
        }) or {}
        self._chamar("notifications/initialized", {}, notificacao=True)
        self._pronto = True
        return resultado

    def ferramentas(self) -> list[dict]:
        """O que este servidor oferece, pelo nome que ele mesmo dá."""
        self.conectar()
        return list((self._chamar("tools/list", {}) or {}).get("tools") or [])

    def chamar_ferramenta(self, nome: str, argumentos: dict | None = None) -> Any:
        """Uma ferramenta do CHUB, já desembrulhada da casca do MCP."""
        self.conectar()
        resultado = self._chamar("tools/call", {
            "name": nome,
            "arguments": argumentos or {},
        })
        if isinstance(resultado, dict) and resultado.get("isError"):
            raise ChubError(f"{nome} falhou: {_texto_do_resultado(resultado)}")
        return _texto_do_resultado(resultado)

    # ── Acervo ───────────────────────────────────────────────────────────────

    def blocos(self, video_id: str) -> dict:
        """Todos os blocos publicados de um vídeo, juntando as páginas.

        Devolve no formato que ``acervo_library.convert`` espera receber, que é
        o formato do próprio servidor — a junção só concatena `items`.
        """
        pagina = self.chamar_ferramenta("chub_acervo_blocks", {
            "videoId": video_id, "limit": BLOCK_PAGE,
        })
        if not isinstance(pagina, dict):
            raise ChubError(f"resposta inesperada de blocos para {video_id}")
        itens = list(pagina.get("items") or [])
        cursor = pagina.get("nextCursor")
        voltas = 0
        while cursor and voltas < MAX_PAGES:
            voltas += 1
            seguinte = self.chamar_ferramenta("chub_acervo_blocks", {
                "videoId": video_id, "limit": BLOCK_PAGE, "cursor": cursor,
            })
            if not isinstance(seguinte, dict):
                break
            novos = list(seguinte.get("items") or [])
            if not novos:
                break
            itens.extend(novos)
            cursor = seguinte.get("nextCursor")
        pagina["items"] = itens
        pagina.pop("nextCursor", None)
        return pagina

    def transcricao(self, video_id: str) -> dict:
        """A tabela de frases inteira, juntando as páginas.

        As frases são o que dá ao Furia o `turn` e o `speakerChange` já apurados
        pelo Acervo, então parar na primeira página seria trocar o dado bom por
        um pedaço dele.
        """
        pagina = self.chamar_ferramenta("chub_acervo_transcript", {
            "videoId": video_id, "limit": SENTENCE_PAGE,
        })
        if not isinstance(pagina, dict):
            raise ChubError(f"resposta inesperada de transcrição para {video_id}")
        frases = list(pagina.get("sentences") or [])
        proxima = (pagina.get("page") or {}).get("nextSentenceIdx")
        voltas = 0
        while proxima is not None and voltas < MAX_PAGES:
            voltas += 1
            seguinte = self.chamar_ferramenta("chub_acervo_transcript", {
                "videoId": video_id, "limit": SENTENCE_PAGE, "startSentenceIdx": proxima,
            })
            if not isinstance(seguinte, dict):
                break
            novas = list(seguinte.get("sentences") or [])
            if not novas:
                break
            frases.extend(novas)
            proxima = (seguinte.get("page") or {}).get("nextSentenceIdx")
        pagina["sentences"] = frases
        return pagina

    def exportar(self, video_id: str) -> dict:
        """Um vídeo do Acervo no formato que o Furia arquiva por id."""
        from .acervo_library import convert

        return convert(self.blocos(video_id), self.transcricao(video_id))


def videos_do_acervo(cliente: ChubClient, *, limite: int = 500, **filtros) -> Iterator[dict]:
    """Os vídeos que têm bloco publicado, um a um, sem repetir.

    O Acervo não expõe "liste os vídeos"; ele expõe blocos, e cada bloco diz de
    que vídeo saiu. Listar vídeo é então percorrer bloco e guardar o que já
    passou — que é barato, porque o filtro e a paginação são do servidor.
    """
    vistos: set[str] = set()
    cursor = None
    voltas = 0
    while voltas < MAX_PAGES:
        voltas += 1
        argumentos = {"limit": min(limite, BLOCK_PAGE), **filtros}
        if cursor:
            argumentos["cursor"] = cursor
        pagina = cliente.chamar_ferramenta("chub_acervo_blocks", argumentos)
        if not isinstance(pagina, dict):
            return
        itens = pagina.get("items") or []
        if not itens:
            return
        for item in itens:
            video = (item or {}).get("video") if isinstance(item, dict) else None
            if not isinstance(video, dict):
                continue
            youtube_id = str(video.get("youtubeId") or "")
            if not youtube_id or youtube_id in vistos:
                continue
            vistos.add(youtube_id)
            yield video
        cursor = pagina.get("nextCursor")
        if not cursor:
            return
