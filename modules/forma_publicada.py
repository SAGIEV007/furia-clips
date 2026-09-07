"""A forma de um corte que a equipe publicou de verdade.

POR QUE ISTO EXISTE
-------------------
O editor perguntou se os cortes que o Renan já tem no Instagram não poderiam
ensinar o Furia. Podem, e são a maior fonte disponível — 5.339 publicados, cada
um com transcrição.

O que NÃO dá para tirar deles é a hora no vídeo longo. Testado: peguei o corte
mais visto e procurei o texto na sabatina; não bate. No Acervo há 78 blocos, em
pelo menos quatro vídeos diferentes, com o mesmo argumento e palavras diferentes
a cada vez — o Renan repete as teses dele. A busca acha o ARGUMENTO, não a
GRAVAÇÃO, e gabarito com hora errada é pior que gabarito nenhum.

O que dá, e não precisa de alinhamento nenhum, é a **forma**: quanto tempo dura,
como abre, como fecha. Isso está inteiro na transcrição do post.

A REGRA QUE ISTO RESPEITA (NORTE §15)
--------------------------------------
Quem publicou foi a equipe, não o programa. É verdade de fora, do mesmo tipo dos
blocos do Acervo — e diferente de tudo que o Furia diz sobre si mesmo.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

# Uma pergunta de abertura tão curta quanto esta é a que o editor liberou:
# "se for uma pergunta curta do repórter não tem problema mostrar". O corte mais
# visto de todos (9,1 M) abre com 1,5 s de pergunta.
MAX_PERGUNTA_DE_ABERTURA_S = 8.0


def _norm(texto: str) -> str:
    plano = unicodedata.normalize("NFD", str(texto or "").lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", plano)).strip()


def pasta(data_dir=None) -> Path:
    base = Path(
        data_dir or os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
    )
    return base / "publicados"


def ler(data_dir=None) -> list[dict]:
    """Os cortes publicados que estão no disco, como o CHUB os devolve."""
    destino = pasta(data_dir)
    if not destino.is_dir():
        return []
    cortes = []
    for arquivo in sorted(destino.glob("*.json")):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for corte in (dados if isinstance(dados, list) else [dados]):
            if isinstance(corte, dict) and corte.get("script"):
                cortes.append(corte)
    return cortes


def forma(corte: dict) -> dict[str, Any]:
    """As quatro coisas que a transcrição de um post publicado já responde."""
    falas = [f for f in (corte.get("script") or []) if isinstance(f, dict)]
    if not falas:
        return {}
    inicio = min(float(f.get("startS") or 0) for f in falas)
    fim = max(float(f.get("endS") or 0) for f in falas)

    primeira = falas[0]
    quem_abre = str(primeira.get("speaker") or "").lower()
    # "unknown" na transcrição do post é, na prática, quem não é o Renan: o
    # repórter, o âncora, ou alguém da rua. Para a forma do corte o que importa
    # é só se o corte abre nele e por quanto tempo.
    abre_em_outro = quem_abre and quem_abre != "renan"
    duracao_da_abertura = float(primeira.get("endS") or 0) - float(primeira.get("startS") or 0)

    ultima = falas[-1]
    texto_final = str(ultima.get("text") or "").strip()

    return {
        "duracao_s": round(fim - inicio, 1),
        "abre_em_outro": bool(abre_em_outro),
        "abertura_s": round(duracao_da_abertura, 1),
        "abertura_curta": bool(abre_em_outro and duracao_da_abertura <= MAX_PERGUNTA_DE_ABERTURA_S),
        "fecha_com_ponto": bool(re.search(r"[.!?]\s*$", texto_final)),
        "legenda": str(corte.get("caption") or "").strip(),
        "primeira_fala": str(primeira.get("text") or "").strip(),
        "ultima_fala": texto_final,
        "url": corte.get("url", ""),
    }


def legenda_saiu_do_corte(f: dict) -> bool:
    """A legenda do post repete uma frase do próprio corte?

    Nos três mais vistos ela repetia — ou a tese, ou a pergunta que abre. É a
    única evidência de headline que existe hoje sem o editor escrever nada, e os
    dois testes de estilo de headline estão parados esperando exatamente isso.
    """
    legenda = _norm(f.get("legenda", "")).split("siga")[0].strip()
    if len(legenda) < 12:
        return False
    corpo = _norm(f.get("primeira_fala", "") + " " + f.get("ultima_fala", ""))
    palavras = [p for p in legenda.split() if len(p) > 3]
    if not palavras:
        return False
    acertos = sum(1 for p in palavras if p in corpo)
    return acertos / len(palavras) >= 0.5


def medir(cortes: list[dict]) -> dict[str, Any]:
    """O retrato dos cortes publicados, para comparar com o que o Furia entrega."""
    formas = [f for f in (forma(c) for c in cortes) if f]
    if not formas:
        return {"n": 0}
    duracoes = sorted(f["duracao_s"] for f in formas)
    meio = duracoes[len(duracoes) // 2]
    return {
        "n": len(formas),
        "duracao_mediana_s": meio,
        "duracao_min_s": duracoes[0],
        "duracao_max_s": duracoes[-1],
        "abrem_em_outro": sum(1 for f in formas if f["abre_em_outro"]),
        "abertura_curta": sum(1 for f in formas if f["abertura_curta"]),
        "fecham_com_ponto": sum(1 for f in formas if f["fecha_com_ponto"]),
        "legenda_do_corte": sum(1 for f in formas if legenda_saiu_do_corte(f)),
    }
