"""O que o editor de fato publica, lido do corpus em vez de inventado aqui.

`data/estilo/headlines_publicadas.json` foi transcrito das capturas que ele
mandou: dezenove chamadas superiores publicadas de verdade, sete padrões de forma
com os verbos que ele usa, e as palavras que ele sobe para caixa alta. O arquivo
estava no repositório desde 18/08 e nenhuma linha dele chegava ao gerador — que
enquanto isso trabalhava com treze ganchos inventados, dos quais **um só**
coincidia com os dele.

Este módulo é a ponte, e ele carrega uma distinção que o corpus obriga a fazer.
O próprio arquivo avisa:

    Copiar um molde daqui sobre um corte que não o sustenta produz manchete falsa,
    que é pior do que manchete fraca.

Há duas espécies de chamada entre as observadas. Uma é **reação pura** —
"VIRALIZOU!", "NA LATA!", "CHOCADA!", "MEU DEUS!" — que diz apenas o que sentir e
serve a qualquer corte da mesma postura. A outra **carrega conteúdo** — "FIM DO
XANDÃO?", "NEM FLÁVIO, NEM LULA:", "DE MILÍCIA A COMANDO VERMELHO" — e reusá-la
num corte que não fala daquilo é afirmar um fato que o corte não tem. Só a
primeira espécie sai daqui.
"""

from __future__ import annotations

import json
import os

_CAMINHO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "estilo", "headlines_publicadas.json",
)
_CACHE = None

# Sem o corpus o gerador não pode ficar sem gancho nenhum — headline sem chamada
# superior é exatamente a queixa que originou tudo isto. Estes três são os únicos
# que sobrevivem à ausência do arquivo, e são os mais neutros do feed.
_GANCHOS_DE_EMERGENCIA = ("BOMBA!", "OLHA ISSO", "ATENÇÃO")

# Uma chamada que nomeia gente, lugar ou episódio só vale no corte de onde saiu.
_CONTEUDO_NA_CHAMADA = (
    "xandão", "xandao", "flávio", "flavio", "lula", "bolsonaro", "moraes",
    "milícia", "milicia", "comando vermelho", "testosterona", "nikolas",
)


def _ler():
    try:
        with open(_CAMINHO, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, ValueError):
        return {}


def carregar_estilo():
    """O corpus em forma utilizável, ou um vazio honesto se ele não abrir."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    dados = _ler()
    chamadas = dados.get("chamadas_superiores") or {}
    _CACHE = {
        "ganchos": [str(item) for item in (chamadas.get("observadas") or []) if str(item).strip()],
        "ganchos_palavras_max": int(chamadas.get("palavras_max") or 4),
        "padroes": dados.get("padroes") or [],
        "enfase": (dados.get("enfase") or {}).get("palavras_observadas_em_caixa") or [],
        "regras": dados.get("regras_lidas_do_corpus") or [],
    }
    return _CACHE


def ganchos_observados():
    """Todas as chamadas superiores que o editor publicou, como estão no feed."""
    return list(carregar_estilo()["ganchos"])


# E uma terceira espécie, que só aparece quando se olha duas vezes: chamadas que
# afirmam algo sobre o próprio corte. "VIRALIZOU!" e "EM ALTA!" falam da recepção,
# e num corte que acabou de ser gerado isso é simplesmente falso — ele não
# viralizou, ele nem foi publicado. "RESPOSTA HONESTA!" afirma que há uma resposta
# e que ela é honesta, duas coisas que o Furia não tem como saber. Eram
# verdadeiras quando o editor as escolheu à mão, olhando o post; não são
# transferíveis por uma máquina que escolhe antes.
_AFIRMA_SOBRE_O_CORTE = ("viralizou", "em alta", "resposta honesta")


def _carrega_conteudo(gancho):
    baixo = gancho.lower()
    return any(marca in baixo for marca in _CONTEUDO_NA_CHAMADA + _AFIRMA_SOBRE_O_CORTE)


def ganchos_que_transferem():
    """As chamadas que servem a outro corte sem afirmar nada sobre ele.

    Fora ficam as que nomeiam gente ou episódio: elas eram verdadeiras no corte
    de onde saíram e viram manchete falsa em qualquer outro.
    """
    estilo = carregar_estilo()
    limite = estilo["ganchos_palavras_max"]
    transferiveis = [
        gancho for gancho in estilo["ganchos"]
        if not _carrega_conteudo(gancho) and len(gancho.split()) <= limite
    ]
    return transferiveis or list(_GANCHOS_DE_EMERGENCIA)
