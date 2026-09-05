#!/usr/bin/env python3
"""O que o programa aprendeu com o editor — e o gabarito que ele mesmo produz.

O PEDIDO
--------
    "não só o Hermes consiga fazer essas calibrações com base nos feedbacks que
     eu dou, como de preferência, se eu mandar cortes prontos para o Hermes ele
     use para treinar o Furia"

Duas coisas diferentes, e as duas estão aqui:

    --ver          o que os vereditos dele já corrigiram no motor
    --gabarito ID  os cortes que ELE fez viram régua para aquele vídeo

A SEGUNDA É A QUE RESOLVE A LIVE RECENTE
----------------------------------------
Uma live de ontem não está no Acervo, então a régua do CHUB não alcança. Mas se
ele cortou aquela live à mão, ele PRODUZIU o gabarito: o começo e o fim que ele
escolheu são a resposta certa, escrita por quem decide.

    python scripts/aprender.py --gabarito dQw4w9WgXcQ
    python scripts/regua.py --material tests/fixtures/editor_dQw4w9WgXcQ.json

A partir daí é o mesmo laço de sempre — medir, mudar uma coisa, medir de novo —
só que contra o julgamento dele em vez do catálogo.

O QUE PRECISA ESTAR NO DISCO
----------------------------
    ~/FuriaClipsData/vereditos/<rodada>.txt            o que ele respondeu
    ~/FuriaClipsData/vereditos/<rodada>.manifesto.json o que foi enviado
    ~/FuriaClipsData/cortes_do_editor/<qualquer>.txt   os cortes dele

O manifesto é o que liga uma coisa à outra. Sem ele o caderno vira uma lista de
reclamações sem endereço: dá para saber que seis cortes foram reprovados por
"final cortado", mas não se o motor tinha achado aqueles seis fechados — que é
justamente o número que conserta alguma coisa.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from modules.aprendizado import (
    MINIMO_DE_CASOS,
    explicar,
    gabarito_do_editor,
    ler_cortes_do_editor,
    ler_manifestos,
    ler_vereditos,
)

DESTINO = RAIZ / "tests" / "fixtures"


def mostrar():
    vereditos = ler_vereditos()
    enviados = ler_manifestos()
    cortes = ler_cortes_do_editor()
    linhas = explicar()

    print()
    print(f"  {len(vereditos)} veredito(s) · {len(enviados)} corte(s) com manifesto · "
          f"{len(cortes)} corte(s) feito(s) por você")
    print()

    if vereditos and not enviados:
        print("  Os vereditos existem, mas nenhum manifesto.")
        print()
        print("  Sem o manifesto eu sei que você reprovou, e não sei o que o motor")
        print("  tinha achado daquele corte — que é a única informação que conserta")
        print("  alguma coisa. Quem envia os cortes precisa gravar o manifesto junto.")
        print()
        return

    if not linhas:
        print("  Ainda não dá para corrigir nada.")
        print()
        print(f"  Preciso de {MINIMO_DE_CASOS} casos de um mesmo defeito para mexer num")
        print("  peso. Abaixo disso, um clipe reprovado a mais muda o rumo do motor —")
        print("  ele passaria a perseguir o seu último veredito em vez do seu padrão.")
        print()
    else:
        print("  O que o seu julgamento corrigiu no motor:")
        print()
        for linha in linhas:
            sinal = f"{linha['ajuste']:+.0f}%" if linha["ajuste"] else "     "
            print(f"    {linha['peso']:<22} {sinal:>6}   {linha['motivo']}")
        print()
        print("  'cegueira' = você viu o defeito e o motor não. Faz o desconto subir.")
        print("  'alarme falso' = o motor acusou e você aprovou. Faz descer.")
        print()

    if cortes:
        por_video: dict[str, int] = {}
        for corte in cortes:
            por_video[corte["video"]] = por_video.get(corte["video"], 0) + 1
        print("  Os cortes que você fez, por vídeo:")
        for video, quantos in sorted(por_video.items(), key=lambda item: -item[1]):
            pronto = (DESTINO / f"editor_{video}.json").is_file()
            print(f"    {video:<20} {quantos:3} corte(s)   {'régua pronta' if pronto else ''}")
        print()
        print("  Vire qualquer um deles em régua:")
        print(f"    python scripts/aprender.py --gabarito {next(iter(por_video))}")
        print()
    else:
        print("  Você ainda não mandou nenhum corte seu.")
        print()
        print("  É a peça que falta para as lives recentes. O Acervo não tem o vídeo")
        print("  de ontem; você tem — porque cortou. Cada corte seu vira um gabarito")
        print("  para aquele vídeo, e a régua passa a funcionar onde o catálogo não")
        print("  alcança.")
        print()


def montar_gabarito(video: str):
    blocos = gabarito_do_editor(video)
    if not blocos:
        raise SystemExit(f"nenhum corte seu registrado no vídeo {video}")

    caminho_transcricao = DESTINO / f"acervo_{video}.json"
    if caminho_transcricao.is_file():
        base = json.loads(caminho_transcricao.read_text(encoding="utf-8"))
        sentencas = base.get("sentencas") or []
        fonte = dict(base.get("fonte") or {})
    else:
        raise SystemExit(
            f"falta a transcrição de {video}.\n"
            f"Traga com: python scripts/novo_material.py {video}\n"
            "Se o vídeo não estiver no Acervo, a transcrição tem que vir da moagem "
            "do próprio Furia — o gabarito é seu, a transcrição não precisa ser."
        )

    fonte["videoId"] = video
    material = {
        "fonte": fonte,
        "proveniencia": {
            "origem": "cortes_do_editor",
            "aviso": (
                "Os blocos de referência são os cortes que o editor fez à mão. "
                "É o julgamento dele, não o catálogo — e é o único gabarito "
                "possível para material que o Acervo não tem."
            ),
        },
        "blocos_de_referencia": blocos,
        "sentencas": sentencas,
    }
    caminho = DESTINO / f"editor_{video}.json"
    caminho.write_text(json.dumps(material, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(f"  {caminho.relative_to(RAIZ)}")
    print(f"    {len(blocos)} corte(s) seu(s) viraram gabarito · {len(sentencas)} frases")
    print()
    print(f"    medir com:  python scripts/regua.py --material {caminho.relative_to(RAIZ)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="O que o Furia aprendeu com o editor.")
    parser.add_argument("--gabarito", metavar="VIDEO",
                        help="vira os cortes do editor naquele vídeo em régua")
    parser.add_argument("--json", action="store_true", help="só os números")
    args = parser.parse_args()

    if args.gabarito:
        montar_gabarito(args.gabarito)
    elif args.json:
        print(json.dumps({
            "ajustes": explicar(),
            "vereditos": len(ler_vereditos()),
            "cortes_do_editor": len(ler_cortes_do_editor()),
        }, ensure_ascii=False, indent=2))
    else:
        mostrar()


if __name__ == "__main__":
    main()
