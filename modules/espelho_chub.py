"""O que o CHUB sabe, em um arquivo que o Furia lê enquanto corta.

O Furia vinha aprendendo com 71 registros. Era por isso que 55 das suas 58
famílias tinham uma observação só, e por isso que ligar o Campaign Hub não movia
o ranking nem um ponto: não faltava peso, faltava dado.

O banco da campanha tem 29.596 posts com desempenho medido. O que interessa
para cortar são os resumos — quantos exemplos sustentam cada família de gancho,
como cada tema se sai, quem é adversário de quem — e resumo cabe em trinta
quilobytes. Os blocos, que são pesados, continuam vindo um por vídeo.

Três coisas guiaram o formato:

O espelho vem dentro do programa e pode ser substituído por um mais novo na
pasta de dados do editor. Assim ele já chega útil na primeira abertura, sem
depender de o cliente de rede funcionar na máquina dele — coisa que eu não
consigo testar daqui, porque esta máquina não alcança o servidor do CHUB.

Nada aqui decide sozinho. Um sinal fraco continua fraco: o piso de três
observações vale para tudo, e uma família com duas continua neutra.

E onde o dado não decide, o espelho diz que não decide. O mapa de papéis é o
caso claro: Flávio Bolsonaro aparece 640 vezes como adversário contra 100 como
aliado — isso é uma posição. Romeu Zema aparece 62 contra 60, e isso não é
posição nenhuma. Tratar os dois do mesmo jeito seria inventar uma certeza.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

PACOTE = Path(__file__).resolve().parents[1] / "data" / "espelho_chub.json"

# Abaixo disto um número é anedota. Vale para gancho, tema e papel.
MINIMO_DE_OBSERVACOES = 3


def caminho_local(data_dir=None) -> Path:
    """O espelho atualizado pelo editor, que tem precedência sobre o do pacote."""
    base = Path(data_dir or os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData"))
    return base / "chub" / "espelho.json"


def _ler(caminho: Path) -> dict[str, Any] | None:
    try:
        conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return conteudo if isinstance(conteudo, dict) and conteudo.get("ganchos") else None


@lru_cache(maxsize=4)
def _carregar(data_dir: str | None = None) -> dict[str, Any]:
    return _ler(caminho_local(data_dir)) or _ler(PACOTE) or {}


def carregar(data_dir=None) -> dict[str, Any]:
    return _carregar(str(data_dir) if data_dir else None)


def recarregar() -> None:
    """Depois de o chub.bat gravar um espelho novo, esquecer o antigo."""
    _carregar.cache_clear()


def _plano(texto: Any) -> str:
    reduzido = unicodedata.normalize("NFKD", str(texto or "").lower())
    reduzido = "".join(c for c in reduzido if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", reduzido).split())


def gancho(familia: str, conta: str = "@renansantosmbl",
           plataforma: str = "instagram", data_dir=None) -> dict[str, Any] | None:
    """Como essa família de gancho se saiu, se houver exemplos que bastem."""
    alvo = str(familia or "").strip().lower()
    for item in carregar(data_dir).get("ganchos") or []:
        if (item.get("familia") == alvo
                and item.get("conta") == conta
                and item.get("plataforma") == plataforma
                and int(item.get("n") or 0) >= MINIMO_DE_OBSERVACOES):
            return dict(item)
    return None


def familias_conhecidas(data_dir=None) -> list[str]:
    """Toda família que o espelho carrega — inclusive as que o Furia não detecta."""
    return sorted({str(item.get("familia")) for item in carregar(data_dir).get("ganchos") or []})


def tema(slug: str, conta: str = "@renansantosmbl", data_dir=None) -> dict[str, Any] | None:
    alvo = _plano(slug)
    melhor = None
    for item in carregar(data_dir).get("temas") or []:
        if item.get("conta") != conta or _plano(item.get("slug")) != alvo:
            continue
        if int(item.get("n") or 0) < MINIMO_DE_OBSERVACOES:
            continue
        if melhor is None or int(item.get("n") or 0) > int(melhor.get("n") or 0):
            melhor = item
    return dict(melhor) if melhor else None


@lru_cache(maxsize=4)
def _indice_de_papeis(data_dir: str | None = None) -> tuple[tuple[str, dict], ...]:
    """Cada nome entra no índice por todas as grafias em que ele aparece.

    Só pelo nome canônico o mapa perde justamente o caso que interessa: o
    espelho guarda "Romeu Zema", e o trecho falado diz "Zema" — que é como as
    pessoas realmente falam. As variantes vêm do próprio extrator do CHUB, então
    são as formas que de fato ocorrem, não invenção minha.
    """
    indice: list[tuple[str, dict]] = []
    for item in _carregar(data_dir).get("papeis") or []:
        grafias = {str(item.get("nome") or "")}
        grafias.update(str(v) for v in item.get("variantes") or [])
        for grafia in grafias:
            chave = _plano(grafia)
            if len(chave) >= 4:
                indice.append((chave, item))
    # Nome mais longo primeiro: senão "Renan" seria achado dentro de
    # "Renan Calheiros" e o mapa erraria de pessoa.
    indice.sort(key=lambda par: -len(par[0]))
    return tuple(indice)


def papel(nome: str, data_dir=None) -> dict[str, Any] | None:
    """De que lado está esse nome, e com quanta certeza."""
    alvo = _plano(nome)
    if not alvo:
        return None
    for chave, item in _indice_de_papeis(str(data_dir) if data_dir else None):
        if chave == alvo:
            return dict(item)
    return None


def papeis_no_texto(texto: str, data_dir=None) -> list[dict[str, Any]]:
    """Quem aparece neste trecho e de que lado está.

    É isto que permite tratar um adversário se enrolando como material tão bom
    quanto uma boa fala do Renan: o programa passa a saber quem é quem sem
    precisar que alguém digite a lista.

    Quem está marcado como indefinido vem junto, com o rótulo, e nunca some — a
    dúvida é informação, e esconder um empate de 62 a 60 seria pior que mostrar.
    """
    plano = _plano(texto)
    if not plano:
        return []
    # Quem casa mais longo fica com o pedaço. Sem isso "Flávio Bolsonaro" também
    # acusava Jair — pelo sobrenome — e "Renan Calheiros" acusava Renan Santos
    # pelo primeiro nome, transformando um aliado em presença fantasma e um
    # adversário em dois.
    tomados: list[tuple[int, int]] = []
    achados = []
    vistos: set[str] = set()
    for chave, item in _indice_de_papeis(str(data_dir) if data_dir else None):
        padrao = rf"(?<![a-z0-9]){re.escape(chave)}(?![a-z0-9])"
        for encontro in re.finditer(padrao, plano):
            inicio, fim = encontro.span()
            if any(inicio < ate and de < fim for de, ate in tomados):
                continue
            tomados.append((inicio, fim))
            if item["nome"] not in vistos:
                achados.append(dict(item))
                vistos.add(item["nome"])
    achados.sort(key=lambda item: -int(item.get("marcacoes") or 0))
    return achados


def formato(nome: str, data_dir=None) -> dict[str, Any] | None:
    alvo = _plano(nome)
    for item in carregar(data_dir).get("formatos") or []:
        if _plano(item.get("nome")) == alvo:
            return dict(item)
    return None


def descrever(data_dir=None) -> dict[str, Any]:
    """A linha que o editor lê para saber se o espelho chegou e de quando é."""
    espelho = carregar(data_dir)
    if not espelho:
        return {"disponivel": False, "resumo": "Nenhum espelho do CHUB encontrado."}
    ganchos = espelho.get("ganchos") or []
    fonte = espelho.get("fonte") or {}
    local = caminho_local(data_dir)
    mais_forte = max(ganchos, key=lambda item: int(item.get("n") or 0), default={})
    return {
        "disponivel": True,
        "gerado_em": espelho.get("gerado_em", ""),
        "origem": "pasta de dados" if local.is_file() else "instalado com o programa",
        "ganchos": len(ganchos),
        "temas": len(espelho.get("temas") or []),
        "papeis": len(espelho.get("papeis") or []),
        "maior_amostra": int(mais_forte.get("n") or 0),
        "posts_medidos": int(fonte.get("posts_com_desempenho") or 0),
        "resumo": (
            f"{len(ganchos)} medições de gancho, {len(espelho.get('temas') or [])} temas e "
            f"{len(espelho.get('papeis') or [])} nomes mapeados, sobre "
            f"{format(int(fonte.get('posts_com_desempenho') or 0), ',d').replace(',', '.')} posts"
        ),
    }
