#!/usr/bin/env python3
"""Trazer os blocos do Acervo para o Furia, por vídeo ou em lote.

Uso, com o endereço do CHUB no ambiente (ele carrega a credencial, então nunca
escreva num arquivo do projeto):

    export FURIA_CHUB_MCP_URL='valor-fornecido-no-ambiente'

    python scripts/sincronizar_acervo.py --testar
    python scripts/sincronizar_acervo.py KpjvWf9SsWQ fZpyzDpnA2o
    python scripts/sincronizar_acervo.py --listar
    python scripts/sincronizar_acervo.py --tudo --limite 50
    python scripts/sincronizar_acervo.py --vincular "PENELOPE.mp4" abc123XYZ_1

Renomear um download desliga o Acervo em silêncio, porque tudo depende dos onze
caracteres do id do YouTube no nome do arquivo. ``--vincular`` é a saída sem
renomear nada: ele anota, em ~/FuriaClipsData/acervo/vinculos.json, qual vídeo
do Acervo é aquele arquivo.

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

from modules.acervo_library import bind, describe_snapshot, library_dir  # noqa: E402
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


def mostrar_espelho() -> int:
    """A conferência da etapa 1: o que o Furia tem em mãos e de quando é.

    O número que importa aqui é o tamanho da amostra. Se `tese-provocativa`
    disser 482 onde o arquivo antigo dizia 6, o espelho chegou.
    """
    from modules.espelho_chub import caminho_local, carregar, descrever

    resumo = descrever()
    if not resumo.get("disponivel"):
        print("Nenhum espelho encontrado.", file=sys.stderr)
        return 1

    espelho = carregar()
    print(f"{resumo['resumo']}")
    print(f"gerado em {str(resumo.get('gerado_em',''))[:10]} · {resumo['origem']}")
    print(f"local esperado para atualizacoes: {caminho_local()}")

    print("\nganchos (@renansantosmbl · instagram) — mediana de desempenho:")
    ganchos = [g for g in espelho["ganchos"]
               if g["conta"] == "@renansantosmbl" and g["plataforma"] == "instagram"]
    for item in sorted(ganchos, key=lambda g: -g["mediana"]):
        marca = "  <-- o melhor" if item["mediana"] == max(g["mediana"] for g in ganchos) else ""
        print(f"  {item['familia']:<24} n={item['n']:<4} mediana={item['mediana']:.3f}{marca}")

    temas = [t for t in espelho["temas"] if t["conta"] == "@renansantosmbl"]
    temas.sort(key=lambda t: -t["mediana"])
    print(f"\ntemas (@renansantosmbl) — {len(temas)} medidos, os 5 melhores e os 5 piores:")
    for item in temas[:5] + temas[-5:]:
        print(f"  {item['slug']:<28} n={item['n']:<4} mediana={item['mediana']:.3f}")

    papeis = espelho["papeis"]
    contra = [p for p in papeis if p["lado"] == "adversario"]
    duvida = [p for p in papeis if p["lado"] == "indefinido"]
    print(f"\nmapa de nomes: {len(papeis)} pessoas · {len(contra)} adversarios · "
          f"{len(duvida)} sem lado definido")
    for item in contra[:8]:
        print(f"  {item['nome']:<24} adversario   {item['contra']} contra / {item['a_favor']} a favor")
    if duvida:
        print(f"\n  sem lado definido (o Furia NAO vai trata-los como adversario):")
        print("  " + ", ".join(item["nome"] for item in duvida))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("videos", nargs="*", help="ids do YouTube a sincronizar")
    parser.add_argument("--testar", action="store_true", help="só confirmar que a credencial funciona")
    parser.add_argument("--listar", action="store_true", help="listar os vídeos com bloco publicado")
    parser.add_argument("--tudo", action="store_true", help="sincronizar todos os vídeos do Acervo")
    parser.add_argument("--limite", type=int, default=25, help="teto de vídeos para --listar/--tudo")
    parser.add_argument("--forcar", action="store_true", help="refazer export que já existe")
    parser.add_argument(
        "--vincular", nargs=2, metavar=("ARQUIVO", "ID"),
        help="dizer qual vídeo do YouTube é um arquivo cujo nome não traz o id",
    )
    parser.add_argument(
        "--espelho", action="store_true",
        help="mostrar o espelho do CHUB em uso (ganchos, temas e mapa de nomes)",
    )
    args = parser.parse_args()

    if args.espelho:
        return mostrar_espelho()

    # Vincular não fala com o CHUB: é só um bilhete local dizendo qual vídeo é
    # qual. Vem antes de tudo para funcionar mesmo sem credencial configurada.
    if args.vincular:
        arquivo, identificador = args.vincular
        try:
            feito = bind(arquivo, identificador)
        except ValueError as erro:
            print(f"ERRO: {erro}", file=sys.stderr)
            return 2
        print(f"'{feito['arquivo']}' agora é o vídeo {feito['youtube_id']}.")
        print(f"anotado em {feito['vinculos']}")
        destino = library_dir() / f"{feito['youtube_id']}.json"
        if destino.is_file():
            pronto = describe_snapshot(destino)
            print(f"os {pronto['blocks']} blocos desse vídeo já estão baixados; o Furia vai usá-los.")
        else:
            print(f"agora baixe os blocos: chub.bat {feito['youtube_id']}")
        return 0

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
