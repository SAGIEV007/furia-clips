#!/usr/bin/env python3
"""Trazer material novo do Acervo, já com gabarito, para a régua medir.

POR QUE ISTO EXISTE
-------------------
O editor pediu que o Hermes ficasse "baixando de forma autônoma vídeos,
testando, e que de fato estivesse aprendendo".

Baixar vídeo aleatório do YouTube não ensina nada: sem gabarito não há como
saber se o corte ficou bom, e um agente medindo o próprio trabalho passa a noite
produzindo confiança errada.

O Acervo resolve isso porque entrega as duas coisas **juntas**: a transcrição
com tempo (o material) e os blocos temáticos QA-gated (a resposta certa,
supervisionada por gente). Cada vídeo do Acervo já é um exercício com gabarito.

São 5.391 blocos com o Renan falando e mais de um minuto de duração. Material
para muitas noites.

USO
---
    export FURIA_CHUB_MCP_URL='https://.../mcp/wk_...'

    python scripts/novo_material.py --listar               # o que há para pegar
    python scripts/novo_material.py BEC7wmJez0o            # traz um vídeo
    python scripts/novo_material.py --sortear              # um que ainda não veio

Os arquivos vão para `tests/fixtures/acervo_<id>.json`, no mesmo formato que a
régua já lê. Depois:

    python scripts/regua.py --material tests/fixtures/acervo_BEC7wmJez0o.json

ONDE ESTE ARQUIVO PARA
----------------------
Ele **não** baixa o vídeo em si — só a transcrição e o gabarito, que é o que a
régua precisa. Baixar o arquivo de vídeo é outra coisa, mais cara e mais lenta, e
só faz falta quando o teste envolve imagem ou áudio de verdade.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from modules.chub_client import ChubClient, ChubError, videos_do_acervo

DESTINO = RAIZ / "tests" / "fixtures"

# Um bloco que o Acervo marcou com zero cortes possíveis não é material de
# treino: o próprio curador disse que dali não sai clipe. Cobrá-lo do Furia
# seria cobrar o que ninguém acha que existe.
MINIMO_DE_CORTES = 1


def _num(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def montar(cliente: ChubClient, video_id: str) -> dict:
    """Um vídeo do Acervo no formato que `scripts/regua.py` lê."""
    resposta_blocos = cliente.blocos(video_id)
    itens = list(resposta_blocos.get("items") or [])
    if not itens:
        raise ChubError(f"o Acervo não tem bloco publicado para {video_id}")

    video = (itens[0].get("video") or {})
    blocos = []
    for item in sorted(itens, key=lambda b: _num(b.get("startS"))):
        cortes = int(item.get("possibleCuts") or 0)
        if cortes < MINIMO_DE_CORTES:
            continue
        blocos.append({
            "start": round(_num(item.get("startS")), 2),
            "end": round(_num(item.get("endS")), 2),
            "dur": round(_num(item.get("durationS")), 2),
            "cortes": cortes,
            "titulo": str(item.get("title") or ""),
            "q": str(item.get("triggerQuestion") or ""),
            # Guardados porque a régua pode querer separar bloco que se sustenta
            # sozinho de bloco que depende de contexto de fora.
            "precisa_de_contexto": bool(item.get("needsContext")),
            "autossuficiencia_rank": item.get("selfContainedRank"),
        })
    if not blocos:
        raise ChubError(
            f"{video_id} não tem nenhum bloco com corte possível; não serve de gabarito"
        )

    resposta_frases = cliente.transcricao(video_id)
    frases = []
    for frase in resposta_frases.get("sentences") or []:
        texto = str(frase.get("text") or "").strip()
        if not texto:
            continue
        frases.append({
            "start": round(_num(frase.get("startS")), 2),
            "end": round(_num(frase.get("endS")), 2),
            "text": texto,
            "turn": frase.get("turn"),
            "speaker_change": bool(frase.get("speakerChange")),
        })
    if not frases:
        raise ChubError(f"o Acervo não tem transcrição para {video_id}")

    return {
        "fonte": {
            "videoId": video.get("youtubeId") or video_id,
            "url": video.get("url", ""),
            "titulo": video.get("title", ""),
            "duracao_total_s": _num(video.get("durationS")),
            "canal": video.get("channel", ""),
            "trust": itens[0].get("trustTier", ""),
        },
        "proveniencia": {
            "origem": "acervo_chub",
            "aviso": (
                "Legenda automática do YouTube: evidência para análise e navegação, "
                "nunca citação. O áudio é a fonte da verdade."
            ),
        },
        "blocos_de_referencia": blocos,
        "sentencas": frases,
    }


def main():
    parser = argparse.ArgumentParser(description="Traz material do Acervo com gabarito.")
    parser.add_argument("videos", nargs="*", help="ids do YouTube")
    parser.add_argument("--listar", action="store_true", help="mostra o que há para pegar")
    parser.add_argument("--sortear", action="store_true", help="pega um que ainda não veio")
    parser.add_argument("--minimo-blocos", type=int, default=4,
                        help="ignora vídeo com menos blocos que isto (padrão 4)")
    args = parser.parse_args()

    try:
        cliente = ChubClient()
    except ChubError as erro:
        raise SystemExit(f"CHUB não configurado: {erro}")

    if args.listar or args.sortear:
        ja_temos = {p.stem.replace("acervo_", "") for p in DESTINO.glob("acervo_*.json")}
        encontrados = []
        try:
            for video in videos_do_acervo(cliente, limite=120, renanSpeaking=True, minDurationS=60):
                identificador = video.get("youtubeId") or video.get("id")
                if not identificador:
                    continue
                encontrados.append((identificador, video.get("title", ""), identificador in ja_temos))
        except ChubError as erro:
            raise SystemExit(f"não deu para listar: {erro}")

        if args.listar:
            print(f"\n  {len(encontrados)} vídeo(s) do Acervo com bloco publicado:\n")
            for identificador, titulo, temos in encontrados:
                marca = "já temos" if temos else "        "
                print(f"    {marca}  {identificador}  {titulo[:64]}")
            print()
            return

        novos = [v for v in encontrados if not v[2]]
        if not novos:
            print("  Todo vídeo listado já virou material. Nada novo para sortear.")
            return
        args.videos = [novos[0][0]]
        print(f"  Sorteado: {novos[0][0]} — {novos[0][1][:60]}")

    if not args.videos:
        raise SystemExit("informe ao menos um id, ou use --listar / --sortear")

    DESTINO.mkdir(parents=True, exist_ok=True)
    for video_id in args.videos:
        try:
            material = montar(cliente, video_id)
        except ChubError as erro:
            print(f"  {video_id}: {erro}")
            continue
        caminho = DESTINO / f"acervo_{material['fonte']['videoId']}.json"
        caminho.write_text(json.dumps(material, ensure_ascii=False, indent=1), encoding="utf-8")
        print(
            f"  {caminho.relative_to(RAIZ)}\n"
            f"    {len(material['sentencas'])} frases · "
            f"{len(material['blocos_de_referencia'])} blocos com gabarito · "
            f"{sum(b['cortes'] for b in material['blocos_de_referencia'])} cortes esperados"
        )
        print(f"    medir com:  python scripts/regua.py --material {caminho.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
