#!/usr/bin/env python3
"""Trazer os blocos do Acervo para o Furia, por vídeo ou em lote.

Uso, com o endereço do CHUB no ambiente (ele carrega a credencial, então nunca
escreva num arquivo do projeto):

    export FURIA_CHUB_MCP_URL='https://chub-api.missao.org.br/mcp/wk_...'

    python scripts/sincronizar_acervo.py --testar
    python scripts/sincronizar_acervo.py KpjvWf9SsWQ fZpyzDpnA2o
    python scripts/sincronizar_acervo.py --listar
    python scripts/sincronizar_acervo.py --tudo --limite 50

Os exports vão para ``~/FuriaClipsData/acervo/{id}.json``, que é onde o Furia já
procura sozinho quando reconhece o id do YouTube no nome do arquivo de vídeo.

Um vídeo já baixado não é rebaixado sem ``--forcar``: o Acervo republica blocos
quando a rotulagem muda, mas quase sempre a resposta é a mesma e a viagem é cara.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.acervo_library import describe_snapshot, library_dir  # noqa: E402
from modules.chub_client import ChubClient, ChubError, videos_do_acervo  # noqa: E402


def _mmss(segundos) -> str:
    try:
        total = int(float(segundos))
    except (TypeError, ValueError):
        return "?"
    return f"{total // 60}:{total % 60:02d}"


def testar(cliente: ChubClient) -> int:
    """Uma chamada barata que prova que a credencial funciona."""
    ferramentas = cliente.ferramentas()
    nomes = sorted(str(item.get("name") or "") for item in ferramentas)
    acervo = [nome for nome in nomes if "acervo" in nome]
    print(f"conectado · {len(nomes)} ferramentas · {len(acervo)} do Acervo")
    for nome in acervo:
        print(f"  {nome}")
    if not acervo:
        print("\nAVISO: nenhuma ferramenta de Acervo neste servidor.", file=sys.stderr)
        return 1
    return 0


def listar(cliente: ChubClient, limite: int) -> int:
    print(f"{'id':<14} {'dur':>7}  título")
    total = 0
    for video in videos_do_acervo(cliente):
        total += 1
        print(f"{str(video.get('youtubeId')):<14} {_mmss(video.get('durationS')):>7}  "
              f"{str(video.get('title') or '')[:64]}")
        if total >= limite:
            break
    print(f"\n{total} vídeo(s) com bloco publicado")
    return 0


def baixar(cliente: ChubClient, video_id: str, *, forcar: bool) -> bool:
    destino = library_dir() / f"{video_id}.json"
    if destino.is_file() and not forcar:
        pronto = describe_snapshot(destino)
        print(f"  {video_id}  já existe ({pronto['blocks']} blocos) — use --forcar para refazer")
        return True
    try:
        export = cliente.exportar(video_id)
    except ChubError as erro:
        print(f"  {video_id}  FALHOU: {erro}", file=sys.stderr)
        return False

    if not (export.get("records") or {}).get("blocks"):
        print(f"  {video_id}  sem bloco publicado no Acervo — nada a gravar")
        return False

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
    cobertura = export.get("coverage") or {}
    pronto = describe_snapshot(destino)
    print(f"  {video_id}  {pronto['blocks']:>3} blocos · {pronto['sentences']:>5} frases "
          f"({cobertura.get('sentences_outside_blocks', 0)} fora de bloco) · "
          f"{pronto['possible_cuts']:>3} cortes previstos · {pronto['title'][:40]}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("videos", nargs="*", help="ids do YouTube a sincronizar")
    parser.add_argument("--testar", action="store_true", help="só confirmar que a credencial funciona")
    parser.add_argument("--listar", action="store_true", help="listar os vídeos com bloco publicado")
    parser.add_argument("--tudo", action="store_true", help="sincronizar todos os vídeos do Acervo")
    parser.add_argument("--limite", type=int, default=25, help="teto de vídeos para --listar/--tudo")
    parser.add_argument("--forcar", action="store_true", help="refazer export que já existe")
    args = parser.parse_args()

    if not (args.videos or args.testar or args.listar or args.tudo):
        parser.print_help()
        return 2

    try:
        cliente = ChubClient()
    except ChubError as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        print("\nO endereço é aquele que você usou como conector, inteiro, com o "
              "'wk_...' no fim.", file=sys.stderr)
        return 2

    try:
        if args.testar:
            return testar(cliente)
        if args.listar:
            return listar(cliente, args.limite)

        alvos = list(args.videos)
        if args.tudo:
            for video in videos_do_acervo(cliente):
                youtube_id = str(video.get("youtubeId") or "")
                if youtube_id and youtube_id not in alvos:
                    alvos.append(youtube_id)
                if len(alvos) >= args.limite:
                    break

        print(f"sincronizando {len(alvos)} vídeo(s) para {library_dir()}\n")
        bons = sum(1 for video_id in alvos if baixar(cliente, video_id, forcar=args.forcar))
        print(f"\n{bons}/{len(alvos)} com blocos no Acervo")
        return 0 if bons else 1
    except ChubError as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrompido", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
