#!/usr/bin/env python3
"""A segunda régua: o Furia medido contra o julgamento do editor.

POR QUE ELA EXISTE
------------------
O editor pediu que o programa "aprendesse com os cortes que eu fizesse e
aprovasse".

O caderno de vereditos já recolhe isso — ele responde `3 ok`, `4 ok mas final
cortado`, `7 nao abre no apresentador` pelo WhatsApp, e vira linha no caderno.
Mas até agora **nenhum código lia esse caderno**. Os vereditos morriam no
arquivo.

Esta régua lê. E ela é a mais valiosa das duas, porque o Acervo diz onde o
assunto começa e termina — o editor diz o que **serve**, que não é a mesma
coisa.

USO
---
    python scripts/regua_vereditos.py
    python scripts/regua_vereditos.py --pasta ~/FuriaClipsData/vereditos
    python scripts/regua_vereditos.py --json

O QUE ELA PROCURA
-----------------
A pergunta que interessa não é "quantos ele aprovou" — é **onde a opinião dele
discorda do que o programa achou de si mesmo**. Cinco cortes que ele marcou com
"final cortado" e que o Furia tinha marcado como "fecho completo" são um erro de
calibração localizado, com nome e endereço. Isso é ouro, e é o único jeito de a
nota do programa parar de mentir.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

PASTA_PADRAO = Path(
    os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
) / "vereditos"

# As etiquetas que o caderno usa, e o sinal do motor que cada uma acusa. É este
# par que transforma "não gostei" em "conserte isto aqui".
O_QUE_CADA_ETIQUETA_ACUSA = {
    "fim": ("payoff_complete", "o motor achou que o fecho estava completo"),
    "abertura": ("starts_mid_sentence", "o motor não viu que abria no meio"),
    "locutor": ("opens_without_a_claim", "o motor não viu quem estava falando"),
    "contexto": ("context_complete", "o motor achou que o contexto estava completo"),
    "longo": ("duration_fit", "o motor achou a duração adequada"),
    "curto": ("duration_fit", "o motor achou a duração adequada"),
    "repetido": ("diversity_penalty", "o motor não viu a repetição"),
}


def ler_caderno(pasta: Path) -> list[dict]:
    """Toda linha de veredito, de todas as rodadas, a mais recente por corte.

    O caderno só acrescenta linha — ele nunca reescreve — então um corte pode
    ter mais de um veredito quando o editor muda de ideia. A última vale, e as
    anteriores continuam no arquivo porque apagar histórico de julgamento é
    apagar o motivo de a régua existir.
    """
    if not pasta.is_dir():
        return []
    por_corte: dict[tuple[str, str], dict] = {}
    for arquivo in sorted(pasta.glob("*.txt")):
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4:
                continue
            quando, rodada, numero, veredito = partes[0], partes[1], partes[2], partes[3]
            etiqueta = partes[4] if len(partes) > 4 else ""
            motivo = partes[5] if len(partes) > 5 else ""
            if not veredito:
                continue
            por_corte[(rodada, numero)] = {
                "quando": quando, "rodada": rodada, "numero": numero.lstrip("#"),
                "veredito": veredito.replace("-", " ").strip(),
                "etiqueta": etiqueta, "motivo": motivo,
            }
    return list(por_corte.values())


def medir(vereditos: list[dict]) -> dict:
    contagem = Counter(v["veredito"] for v in vereditos)
    etiquetas = Counter(v["etiqueta"] for v in vereditos if v["etiqueta"])
    serviram = contagem.get("ok", 0) + contagem.get("ok mas", 0)
    return {
        "total": len(vereditos),
        "ok": contagem.get("ok", 0),
        "ok_mas": contagem.get("ok mas", 0),
        "nao": contagem.get("nao", 0),
        "serviram": serviram,
        "aproveitamento": round(100 * serviram / max(1, len(vereditos))),
        "etiquetas": dict(etiquetas.most_common()),
    }


def imprimir(numeros: dict, vereditos: list[dict]):
    print()
    if not numeros["total"]:
        print("  O caderno está vazio.")
        print()
        print("  Ele enche sozinho enquanto você revisa pelo celular: responda")
        print("  '3 ok', '4 ok mas final cortado', '7 nao abre no apresentador'.")
        print("  Com trinta vereditos etiquetados dá para calibrar no seu julgamento")
        print("  em vez do meu.")
        print()
        return

    print(f"  {numeros['total']} vereditos no caderno")
    print()
    print(f"    serviu como está ........ {numeros['ok']:3}")
    print(f"    serviu com ressalva ..... {numeros['ok_mas']:3}")
    print(f"    não serviu .............. {numeros['nao']:3}")
    print(f"    aproveitamento .......... {numeros['aproveitamento']:3}%")
    print()

    if numeros["etiquetas"]:
        print("  O que mais custa a ele, em ordem:")
        for etiqueta, quantas in numeros["etiquetas"].items():
            sinal, leitura = O_QUE_CADA_ETIQUETA_ACUSA.get(etiqueta, ("", ""))
            explicacao = f"  →  {leitura}" if leitura else ""
            print(f"    {etiqueta:<12} {quantas:3}{explicacao}")
        print()
        principal = next(iter(numeros["etiquetas"]))
        sinal, leitura = O_QUE_CADA_ETIQUETA_ACUSA.get(principal, ("", ""))
        if sinal:
            print(f"  Onde olhar primeiro: o sinal `{sinal}` do motor.")
            print(f"  {numeros['etiquetas'][principal]} vez(es) o editor discordou dele.")
            print()

    if numeros["total"] < 20:
        print(f"  Ainda são poucos ({numeros['total']}). Abaixo de vinte, uma etiqueta")
        print("  a mais muda a ordem inteira — leia como pista, não como conclusão.")
        print()


def main():
    parser = argparse.ArgumentParser(description="Mede o Furia contra o julgamento do editor.")
    parser.add_argument("--pasta", default=str(PASTA_PADRAO), help="onde está o caderno")
    parser.add_argument("--json", action="store_true", help="devolve só os números")
    args = parser.parse_args()

    vereditos = ler_caderno(Path(args.pasta).expanduser())
    numeros = medir(vereditos)

    if args.json:
        print(json.dumps(numeros, ensure_ascii=False, indent=2))
    else:
        imprimir(numeros, vereditos)


if __name__ == "__main__":
    main()
