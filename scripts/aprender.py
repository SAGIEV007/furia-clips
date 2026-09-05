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
    _pasta,
    explicar,
    gabarito_do_editor,
    ler_cortes_do_editor,
    ler_do_programa,
    ler_vereditos,
)

DESTINO = RAIZ / "tests" / "fixtures"


def onde_ficam():
    """Os arquivos que viram régua, e onde eles moram.

    Ele usa dois notebooks. Nada disto adianta se ele não souber o que levar de
    um para o outro — e a resposta não é "a pasta do programa": é esta lista,
    curta, com o que existe e o que não existe.
    """
    from config import DB_PATH

    print()
    print("  ONDE FICAM OS SEUS DADOS  (é isto que vai de um notebook para o outro)")
    print()
    itens = [
        (Path(DB_PATH), "seus aprovar/rejeitar e os cortes de cada projeto"),
        (_pasta("cortes_do_editor"), "os cortes que VOCÊ fez, se você anotar algum"),
        (_pasta("vereditos"), "o caderno do WhatsApp (só se você usar o Hermes)"),
        (_pasta("chub"), "o espelho do CHUB, se estiver baixado"),
    ]
    for caminho, para_que in itens:
        existe = caminho.exists()
        marca = "existe" if existe else "ainda não"
        print(f"    {marca:<10} {caminho}")
        print(f"               {para_que}")
    print()
    print("  Para levar de um notebook ao outro, NÃO copie arquivo na mão:")
    print("    no notebook onde você revisou:  botão 'Enviar feedback ao GitHub'")
    print("    no outro notebook:              botão 'Restaurar feedback'")
    print()
    print("  O programa já sabe fazer isso e manda só a decisão, sem transcrição")
    print("  e sem vídeo. Copiar o banco na mão sobrescreve o trabalho do outro lado.")
    print()


def qual_regua(video: str = ""):
    """Qual gabarito existe para um vídeo — o do CHUB, o seu, ou nenhum.

    A pergunta dele, e ela é a certa: dá para saber se o CHUB está sendo usado
    de régua quando o vídeo está lá, e principalmente **quando não está**.
    """
    print()
    print("  QUAL RÉGUA EXISTE, VÍDEO POR VÍDEO")
    print()
    acervo = {p.stem.replace("acervo_", "") for p in DESTINO.glob("acervo_*.json")}
    meus = {p.stem.replace("editor_", "") for p in DESTINO.glob("editor_*.json")}
    cortes_por_video: dict[str, int] = {}
    for corte in ler_cortes_do_editor():
        cortes_por_video[corte["video"]] = cortes_por_video.get(corte["video"], 0) + 1

    videos = sorted(acervo | meus | set(cortes_por_video)) if not video else [video]
    if not videos:
        print("    Nenhum vídeo tem régua ainda, além da sabatina que vem no programa.")
        print()
        print("    Traga um do Acervo:   python scripts/novo_material.py --sortear")
        print("    Ou anote um corte seu e ele vira régua sozinho.")
        print()
        return

    for identificador in videos:
        tem_acervo = identificador in acervo
        quantos_meus = cortes_por_video.get(identificador, 0)
        if tem_acervo and quantos_meus:
            estado = "CHUB + os seus cortes"
        elif tem_acervo:
            estado = "CHUB (blocos do Acervo)"
        elif quantos_meus:
            estado = f"só os seus cortes ({quantos_meus})"
        else:
            estado = "NENHUMA — não dá para medir este vídeo"
        print(f"    {identificador:<18} {estado}")
        if not tem_acervo and not quantos_meus:
            print("                       o Acervo não tem, e você não anotou corte nenhum")
    print()
    print("  Sem régua, o programa ainda corta — ele só não sabe dizer se acertou.")
    print("  É por isso que anotar os SEUS cortes vale tanto numa live recente.")
    print()


def mostrar():
    da_tela, _sinais = ler_do_programa()
    do_caderno = ler_vereditos()
    cortes = ler_cortes_do_editor()
    linhas = explicar()

    print()
    print(f"  {len(da_tela)} veredito(s) que você deu na TELA do programa")
    print(f"  {len(do_caderno)} veredito(s) vindos do caderno do WhatsApp")
    print(f"  {len(cortes)} corte(s) que você mesmo fez e anotou")
    print()

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
    parser.add_argument("--onde", action="store_true",
                        help="mostra onde ficam os arquivos, para levar ao outro notebook")
    parser.add_argument("--regua", nargs="?", const="", metavar="VIDEO",
                        help="diz qual gabarito existe para cada vídeo (CHUB, seus cortes, ou nenhum)")
    parser.add_argument("--json", action="store_true", help="só os números")
    args = parser.parse_args()

    if args.gabarito:
        montar_gabarito(args.gabarito)
    elif args.onde:
        onde_ficam()
    elif args.regua is not None:
        qual_regua(args.regua)
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
