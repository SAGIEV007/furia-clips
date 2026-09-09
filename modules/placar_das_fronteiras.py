"""Quantas viradas de assunto o Furia acerta, contra as que o CHUB marcou.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O editor pediu: "quero uma forma de me certificar de que ele está sendo usado e
fazendo diferença de fato". O número existia — `scripts/regua_assuntos.py` — mas
só rodava digitando um comando num terminal, e ele não usa terminal. Eu mandei
ele rodar mesmo assim, e ele respondeu "esse código é para rodar onde??".

A conta mora aqui para que a tela e a régua usem a MESMA, e não duas parecidas.

O CUIDADO QUE VALE MAIS QUE O NÚMERO
------------------------------------
As fronteiras do CHUB são gabarito, nunca entrada. Se o Furia cortasse usando as
fronteiras do Acervo e depois fosse medido contra elas, o número subiria sem o
corte melhorar e a régua estaria conferindo a própria cola.

A COLUNA ANTI-CHUTE
-------------------
"Achadas" sozinha se conserta propondo mais: quem chuta uma virada a cada dez
segundos acha todas e não sabe nada. Por isso vai junto quantas das fronteiras
PROPOSTAS eram reais.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Quanto uma virada pode errar e ainda contar como achada. Quinze segundos é
# generoso de propósito: a pergunta é se o programa VIU a virada, não se acertou
# o segundo. O mesmo valor da régua de linha de comando.
TOLERANCIA_S = 15.0


def _numero(item: dict[str, Any], *chaves: str) -> float | None:
    """O primeiro dos nomes que existir, como número.

    O export convertido do Acervo guarda `start_s`; os gabaritos da bancada
    guardam `start`. Os dois entram — ler só um nome devolvia zero em silêncio,
    e um placar que diz 0/0 sem reclamar é pior do que placar nenhum.
    """
    for chave in chaves:
        if chave in item and item[chave] is not None:
            try:
                return float(item[chave])
            except (TypeError, ValueError):
                continue
    return None


def _viradas(inicios: list[float]) -> list[float]:
    """Os pontos onde um assunto começa, menos o primeiro.

    O começo do vídeo não é uma virada: todo mundo acerta, e contá-lo infla os
    dois lados da conta sem dizer nada.
    """
    return sorted(inicios)[1:]


def comparar(gabarito: list[float], propostas: list[float],
             tolerancia: float = TOLERANCIA_S) -> dict[str, Any]:
    """As duas colunas, e o detalhe de cada virada do gabarito."""
    detalhe = []
    achadas = 0
    for borda in gabarito:
        if propostas:
            perto = min(propostas, key=lambda proposta: abs(proposta - borda))
            erro = abs(perto - borda)
        else:
            perto, erro = None, float("inf")
        acertou = erro <= tolerancia
        achadas += 1 if acertou else 0
        detalhe.append({
            "gabarito_s": round(borda, 1),
            "furia_s": round(perto, 1) if perto is not None else None,
            "erro_s": round(erro, 1) if erro != float("inf") else None,
            "achou": acertou,
        })

    certeiras = sum(
        1 for proposta in propostas
        if gabarito and min(abs(proposta - borda) for borda in gabarito) <= tolerancia
    )
    return {
        "viradas_no_gabarito": len(gabarito),
        "achadas": achadas,
        "achadas_pct": round(100 * achadas / len(gabarito), 1) if gabarito else 0.0,
        "propostas": len(propostas),
        "certeiras": certeiras,
        "certeiras_pct": round(100 * certeiras / len(propostas), 1) if propostas else 0.0,
        "tolerancia_s": tolerancia,
        "detalhe": detalhe,
    }


def do_acervo(caminho_do_acervo: str | Path) -> dict[str, Any]:
    """As frases e as fronteiras que o CHUB tem para esta fonte.

    Devolve `{}` quando o arquivo não existe ou não é um export do Acervo —
    e quem chama trata isso como "este vídeo não tem gabarito", nunca como erro.
    """
    try:
        dados = json.loads(Path(str(caminho_do_acervo)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    registros = dados.get("records") if isinstance(dados, dict) else None
    if not isinstance(registros, dict):
        return {}

    frases, vistas = [], set()
    for frase in registros.get("sentences") or []:
        if not isinstance(frase, dict):
            continue
        comeco = _numero(frase, "start_s", "start")
        fim = _numero(frase, "end_s", "end")
        texto = " ".join(str(frase.get("text") or "").split())
        if comeco is None or fim is None or fim <= comeco or not texto:
            continue
        # A mesma frase aparece uma vez por bloco que a contém, e a linha do
        # tempo completa é acrescentada depois: sem isto ela entraria em dobro
        # e a curva de coesão leria repetição onde não há.
        chave = (round(comeco, 3), round(fim, 3))
        if chave in vistas:
            continue
        vistas.add(chave)
        frases.append({
            "start": comeco, "end": fim, "text": texto,
            "speaker_change": bool(frase.get("speaker_change")),
        })
    frases.sort(key=lambda item: (item["start"], item["end"]))

    blocos = []
    for bloco in registros.get("blocks") or []:
        if not isinstance(bloco, dict):
            continue
        comeco = _numero(bloco, "start_s", "start")
        if comeco is not None:
            blocos.append({"start": comeco, "titulo": str(bloco.get("title") or "")})
    blocos.sort(key=lambda item: item["start"])

    fontes = registros.get("sources") or []
    primeira = fontes[0] if fontes and isinstance(fontes[0], dict) else {}
    return {
        "frases": frases,
        "blocos": blocos,
        "titulo": str(primeira.get("title") or ""),
        "video_id": str(primeira.get("youtube_id") or ""),
    }


def medir_fonte(caminho_do_acervo: str | Path, seletor) -> dict[str, Any]:
    """O placar desta fonte, pelo MESMO caminho que a moagem usa.

    `seletor` é um `ClipSelector` já com os ajustes da moagem, para o placar
    medir o que de fato vai rodar — com o modelo, se houver chave, ou a leitura
    local. Medir uma cópia do caminho foi como quatro defeitos passaram pelos
    testes esta semana.
    """
    material = do_acervo(caminho_do_acervo)
    if not material or not material["blocos"] or not material["frases"]:
        return {"disponivel": False,
                "motivo": "este vídeo não tem blocos do CHUB neste computador"}

    frases = seletor._build_sentences([dict(f) for f in material["frases"]])
    unidades = seletor._assuntos_do_video(frases)

    # Os dois lados perdem o próprio primeiro começo, pelo mesmo motivo.
    placar = comparar(
        _viradas([bloco["start"] for bloco in material["blocos"]]),
        _viradas([float(unidade["start_s"]) for unidade in unidades]),
    )
    placar.update({
        "disponivel": True,
        "titulo": material["titulo"],
        "video_id": material["video_id"],
        "blocos_do_chub": len(material["blocos"]),
        "assuntos_do_furia": len(unidades),
        "origem": str((getattr(seletor, "_candidate_diagnostics", {}) or {})
                      .get("assuntos_origem") or ""),
    })
    return placar
