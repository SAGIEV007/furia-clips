"""Onde cada assunto começa e termina, dito pelo NÚMERO DA FRASE.

DE ONDE VEIO ESTE ARQUIVO
--------------------------
O editor mandou o link de um bloco do Garimpo e perguntou por que o Furia não
chega perto do que o CHUB faz com um vídeo que nem foi baixado. A pergunta
estava certa e a resposta estava nos dados do próprio CHUB:

    de onde vem o texto ...  legenda automática do YouTube (não baixa vídeo)
    quem analisa .........   um modelo de linguagem
    a receita ............   fronteiras -> correções -> consolidação -> descrição
    tamanho mínimo .......   15 frases por bloco
    endereço .............   startSentenceIdx: 4 · endSentenceIdx: 98

O passo que muda tudo é o último. O CHUB **numera todas as frases do vídeo** —
810 no ato de 7 de setembro — e pergunta ao modelo onde cada assunto começa
**pelo número da frase**. O horário (12,2 s → 401,8 s) não é inventado por
ninguém: sai da tabela de frases.

O QUE O FURIA FAZIA
-------------------
Montava blocos de 50 a 90 segundos e mandava OITO por vez para o modelo. Numa
fonte de 60 minutos isso é uma fresta de oito minutos, umas oito vezes. Não dá
para achar "os 21 assuntos deste vídeo" olhando por uma fresta: assunto é uma
coisa do vídeo inteiro.

E, ao pedir HORÁRIOS em vez de números de frase, o modelo inventava o segundo —
e o programa gastava milhares de linhas consertando a borda depois.

O QUE ESTE ARQUIVO NÃO FAZ
--------------------------
Não escolhe cortes. Ele responde uma pergunta só: onde um assunto acaba e outro
começa. O corte vem depois, por dentro do bloco.

Não fala com serviço nenhum: quem chama passa a função `perguntar`. Assim o
mesmo código serve para o Gemini, para o modelo local e para a bancada de
medição — e nenhum teste precisa de internet.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

# Menor bloco em frases, como o CHUB usa (`min15` no nome da receita dele).
# Serve de proteção contra o modelo picotar o vídeo em pedaços de duas frases.
MINIMO_DE_FRASES = 15

# Quantos caracteres de frase entram no pedido. Frase longa demais é quase
# sempre transcrição sem pontuação; cortar mantém o pedido legível sem mudar o
# assunto, que é o que está sendo julgado.
LIMITE_DA_FRASE = 220


def numerar(frases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A tabela de frases com endereço fixo.

    O endereço é o que permite o modelo apontar sem inventar horário. Ele é
    posicional e imutável dentro de uma moagem: a frase 47 é a frase 47.
    """
    tabela = []
    for indice, item in enumerate(frases or []):
        texto = " ".join(str(item.get("text") or "").split())
        if not texto:
            continue
        try:
            comeco = float(item.get("start", 0) or 0)
            fim = float(item.get("end", 0) or 0)
        except (TypeError, ValueError):
            continue
        if fim <= comeco:
            continue
        tabela.append({
            "idx": indice,
            "start": comeco,
            "end": fim,
            "text": texto,
            "speaker_change": bool(item.get("speaker_change")),
        })
    return tabela


def _relogio(segundos: float) -> str:
    total = int(segundos)
    return f"{total // 60}:{total % 60:02d}"


def _transcricao_numerada(tabela: list[dict[str, Any]]) -> str:
    """A transcrição inteira, uma frase por linha, com número e relógio."""
    return "\n".join(
        f"[{frase['idx']}] {_relogio(frase['start'])}"
        f"{' >>' if frase['speaker_change'] else ''} {frase['text'][:LIMITE_DA_FRASE]}"
        for frase in tabela
    )


def montar_pedido(tabela: list[dict[str, Any]], minimo: int = MINIMO_DE_FRASES) -> str:
    """O vídeo inteiro, numerado, e o que se quer dele."""
    corpo = _transcricao_numerada(tabela)
    return (
        "Você está lendo a transcrição INTEIRA de um vídeo, frase por frase, com o "
        "número de cada frase entre colchetes. ' >>' marca onde quem fala mudou.\n\n"
        "Divida este vídeo em ASSUNTOS. Um assunto é um trecho em que a pessoa "
        "desenvolve uma ideia do começo ao fim: ela levanta um ponto, argumenta e "
        "chega a algum lugar. Quando ela passa a falar de outra coisa, começou "
        "outro assunto.\n\n"
        "Regras:\n"
        f"- cada assunto tem pelo menos {minimo} frases;\n"
        "- os assuntos são contíguos e não se sobrepõem;\n"
        "- abertura, encerramento, pedido de like e conversa de produção NÃO são "
        "assunto: marque-os com \"conteudo\": false;\n"
        "- responda com o NÚMERO da primeira e da última frase de cada assunto, "
        "nunca com horário.\n\n"
        "Responda SÓ com JSON, sem cercas e sem comentário:\n"
        '{"assuntos":[{"inicio":0,"fim":97,"titulo":"frase curta que resume",'
        '"conteudo":true}]}\n\n'
        "TRANSCRIÇÃO:\n" + corpo
    )


def montar_correcao(tabela: list[dict[str, Any]], blocos: list[dict[str, Any]],
                    minimo: int = MINIMO_DE_FRASES) -> str:
    """A segunda passada: mostrar o que saiu e pedir conserto.

    O CHUB roda três passadas — fronteiras, correções, consolidação. Esta é a
    segunda, e existe porque a primeira erra de um jeito específico: parte um
    assunto no meio quando a pessoa dá um exemplo, e junta dois quando eles
    compartilham vocabulário.
    """
    resumo = "\n".join(
        f"- assunto {n}: frases {b['inicio']}–{b['fim']} · {b.get('titulo', '')}"
        for n, b in enumerate(blocos, start=1)
    )
    return (
        "Esta foi a divisão em assuntos que você propôs para a transcrição abaixo:\n\n"
        + resumo
        + "\n\nConfira frase a frase nas fronteiras. Dois erros são comuns:\n"
        "- partir um assunto no meio, quando a pessoa só deu um exemplo;\n"
        "- juntar dois assuntos que só compartilham palavras.\n\n"
        f"Devolva a divisão CORRIGIDA no mesmo formato, com pelo menos {minimo} "
        "frases por assunto. Se estiver certa, devolva igual.\n\n"
        "Responda SÓ com JSON:\n"
        '{"assuntos":[{"inicio":0,"fim":97,"titulo":"...","conteudo":true}]}\n\n'
        "TRANSCRIÇÃO:\n" + _transcricao_numerada(tabela)
    )


def _json_solto(texto: str) -> dict[str, Any]:
    """O JSON que veio, mesmo embrulhado em cerca de markdown."""
    limpo = re.sub(r"^```(?:json)?\s*", "", str(texto or "").strip())
    limpo = re.sub(r"\s*```$", "", limpo)
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        inicio, fim = limpo.find("{"), limpo.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise
        return json.loads(limpo[inicio:fim + 1])


def ler_resposta(texto: str, total: int, minimo: int = MINIMO_DE_FRASES) -> list[dict[str, Any]]:
    """Os assuntos que o modelo devolveu, depois de conferidos.

    Nada aqui confia no modelo. Um endereço fora da transcrição, uma sobreposição
    ou um bloco curto demais é um erro do modelo e some — o que sobra continua
    valendo. Um bloco inventado no meio do nada é pior do que um bloco a menos.
    """
    try:
        dados = _json_solto(texto)
    except (json.JSONDecodeError, ValueError, TypeError):
        return []
    crus = dados.get("assuntos") if isinstance(dados, dict) else None
    if not isinstance(crus, list):
        return []

    limpos = []
    for item in crus:
        if not isinstance(item, dict):
            continue
        try:
            inicio = int(item.get("inicio"))
            fim = int(item.get("fim"))
        except (TypeError, ValueError):
            continue
        if not (0 <= inicio <= fim < total):
            continue
        if fim - inicio + 1 < minimo:
            continue
        limpos.append({
            "inicio": inicio,
            "fim": fim,
            "titulo": " ".join(str(item.get("titulo") or "").split())[:120],
            "conteudo": item.get("conteudo") is not False,
        })

    limpos.sort(key=lambda bloco: (bloco["inicio"], bloco["fim"]))
    sem_sobrepor = []
    for bloco in limpos:
        if sem_sobrepor and bloco["inicio"] <= sem_sobrepor[-1]["fim"]:
            continue
        sem_sobrepor.append(bloco)
    return sem_sobrepor


def assuntos_por_modelo(
    frases: list[dict[str, Any]],
    perguntar: Callable[[str], str],
    *,
    minimo: int = MINIMO_DE_FRASES,
    corrigir: bool = True,
    avisar: Callable[..., None] | None = None,
) -> list[dict[str, Any]]:
    """Os assuntos do vídeo, com início e fim em SEGUNDOS, vindos das frases.

    Devolve lista vazia quando o modelo não responde ou responde coisa que não
    passa na conferência — e vazio quer dizer "use a leitura local", nunca
    "este vídeo não tem assunto". Falhar aqui não pode parar uma moagem.
    """
    tabela = numerar(frases)
    if len(tabela) < minimo * 2:
        return []

    try:
        bruto = perguntar(montar_pedido(tabela, minimo))
    except Exception as erro:  # noqa: BLE001 - nunca derrubar a moagem
        if avisar:
            avisar(f"[Assuntos] O modelo não respondeu ({str(erro)[:90]}); "
                   "vale a leitura local.", "warning")
        return []

    blocos = ler_resposta(bruto, len(tabela), minimo)
    if not blocos:
        if avisar:
            avisar("[Assuntos] A resposta do modelo não passou na conferência; "
                   "vale a leitura local.", "warning")
        return []

    if corrigir:
        try:
            revisado = ler_resposta(
                perguntar(montar_correcao(tabela, blocos, minimo)), len(tabela), minimo)
            # A correção só entra se sobreviver à mesma conferência. Uma segunda
            # passada que devolve lixo não pode apagar uma primeira que estava boa.
            if revisado:
                blocos = revisado
        except Exception:  # noqa: BLE001
            pass

    unidades = []
    for bloco in blocos:
        primeira = tabela[bloco["inicio"]]
        ultima = tabela[bloco["fim"]]
        unidades.append({
            "start_s": primeira["start"],
            "end_s": ultima["end"],
            "duration_s": round(ultima["end"] - primeira["start"], 3),
            "sentence_count": bloco["fim"] - bloco["inicio"] + 1,
            "primeira_frase": bloco["inicio"],
            "ultima_frase": bloco["fim"],
            "titulo": bloco["titulo"],
            "carries_subject": bloco["conteudo"],
            "topic_terms": [],
            "non_content_cues": [],
            "origem": "modelo_por_frase",
        })
    if avisar:
        avisar(f"[Assuntos] O vídeo inteiro foi lido de uma vez: {len(unidades)} "
               f"assunto(s), com a borda no começo de uma frase.", "info")
    return unidades
