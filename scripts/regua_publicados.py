#!/usr/bin/env python3
"""A terceira régua: o corte do Furia comparado com o que a equipe publicou.

AS TRÊS RÉGUAS, E O QUE CADA UMA SABE
-------------------------------------
    regua.py             onde o ASSUNTO começa e termina, segundo o Acervo
    regua_vereditos.py   o que SERVE, segundo o editor
    esta                 que FORMA tem um corte que foi de fato publicado

A terceira nasceu de uma pergunta dele: os cortes do Renan que já estão no
Instagram não podem ensinar o Furia? Podem — a forma deles, não a hora.

O QUE ELA NÃO TENTA FAZER, E POR QUÊ
------------------------------------
Não tenta descobrir de que minuto do vídeo longo cada corte publicado saiu.
Testado: o corte mais visto (9,1 M) não bate com a sabatina, e no Acervo há 78
blocos em pelo menos quatro vídeos diferentes com o mesmo argumento e palavras
diferentes. O Renan repete as teses dele; a busca acha o argumento, não a
gravação. Um gabarito com a hora errada ensinaria o motor a cortar errado com
confiança, que é pior que não ensinar nada.

USO
---
    python scripts/regua_publicados.py --baixar    # traz os publicados do CHUB
    python scripts/regua_publicados.py             # compara com o que o Furia faz
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from modules.forma_publicada import (
    MAX_PERGUNTA_DE_ABERTURA_S,
    ler,
    medir,
    pasta,
)


def furia_agora(material: str = "") -> dict:
    """A mesma forma, medida nos cortes que o Furia entrega hoje."""
    from scripts.regua import carregar_material, moer

    transcricao, _blocos, fonte, _quem = carregar_material(material or None)
    _c, entregues, _a = moer(transcricao)
    if not entregues:
        return {"n": 0}
    duracoes = sorted(float(c.get("end", 0)) - float(c.get("start", 0)) for c in entregues)
    return {
        "n": len(entregues),
        "titulo": fonte.get("titulo", ""),
        "duracao_mediana_s": round(duracoes[len(duracoes) // 2], 1),
        "duracao_min_s": round(duracoes[0], 1),
        "duracao_max_s": round(duracoes[-1], 1),
    }


def imprimir(publicados: dict, furia: dict):
    print()
    if not publicados.get("n"):
        print("  Nenhum corte publicado no disco.")
        print()
        print("  Traga com:  python scripts/regua_publicados.py --baixar")
        print()
        print("  São 5.339 cortes que a equipe publicou de verdade. É a maior fonte")
        print("  de 'como é um corte pronto do Renan' que existe, e ela não exige")
        print("  que você digite nada.")
        print()
        return

    n = publicados["n"]
    print(f"  A FORMA DO QUE FOI PUBLICADO  ({n} cortes da equipe)")
    print()
    print(f"    duração ....................... {publicados['duracao_min_s']:.0f}s a "
          f"{publicados['duracao_max_s']:.0f}s   ·   meio: {publicados['duracao_mediana_s']:.0f}s")
    print(f"    abrem em quem não é o Renan ... {publicados['abrem_em_outro']:3}/{n}")
    print(f"      dessas, abertura curta ...... {publicados['abertura_curta']:3}"
          f"      (até {MAX_PERGUNTA_DE_ABERTURA_S:.0f}s — o que você liberou)")
    print(f"    fecham em frase terminada ..... {publicados['fecham_com_ponto']:3}/{n}")
    print(f"    legenda saiu do próprio corte . {publicados['legenda_do_corte']:3}/{n}")
    print()

    if not furia.get("n"):
        return
    print(f"  O QUE O FURIA ENTREGA  ({furia['n']} cortes · {furia.get('titulo','')[:40]})")
    print()
    print(f"    duração ....................... {furia['duracao_min_s']:.0f}s a "
          f"{furia['duracao_max_s']:.0f}s   ·   meio: {furia['duracao_mediana_s']:.0f}s")
    print()

    meio_pub = publicados["duracao_mediana_s"]
    meio_fur = furia["duracao_mediana_s"]
    if meio_pub and abs(meio_fur - meio_pub) / meio_pub > 0.35:
        maior = "MAIS LONGOS" if meio_fur > meio_pub else "MAIS CURTOS"
        print(f"    Os cortes do Furia são {maior} que os publicados:")
        print(f"    {meio_fur:.0f}s contra {meio_pub:.0f}s no meio da faixa.")
    else:
        print("    A duração bate com a dos publicados.")
    print()
    print("  Isto é evidência de FORMA, não de conteúdo. Um corte do tamanho certo")
    print("  ainda pode estar no lugar errado — quem diz isso é a régua do Acervo,")
    print("  e se ele SERVE, só você.")
    print()


def baixar(quantos: int):
    """Trazer os cortes publicados do CHUB para o disco.

    Guardados em `~/FuriaClipsData/publicados`, junto do resto do material
    local: transcrição do Renan não entra no repositório e não passa por bot.
    """
    try:
        from modules.chub_client import ChubClient, ChubError, endpoint_configurado
    except ImportError as erro:
        raise SystemExit(f"cliente do CHUB indisponível: {erro}")

    url = endpoint_configurado(None)
    if not url:
        raise SystemExit(
            "CHUB não configurado. Aponte FURIA_CHUB_MCP_URL ou grave o endereço em "
            "~/FuriaClipsData/chub-endpoint.txt"
        )

    cliente = ChubClient(url)
    try:
        topo = cliente.chamar_ferramenta("chub_top_posts", {
            "metric": "views", "channel": "@renansantosmbl", "limit": min(50, quantos),
        })
    except ChubError as erro:
        raise SystemExit(f"não deu para listar os publicados: {erro}")

    refs = []
    for linha in (topo.get("rows") or []):
        for endereco in (linha.get("urls") or []):
            refs.append(endereco)
            break
    if not refs:
        raise SystemExit("o CHUB não devolveu nenhum post")

    destino = pasta()
    destino.mkdir(parents=True, exist_ok=True)
    guardados = 0
    # O CHUB aceita até 12 por chamada.
    for inicio in range(0, len(refs), 12):
        lote = refs[inicio:inicio + 12]
        try:
            resposta = cliente.chamar_ferramenta("chub_transcript", {"refs": lote})
        except ChubError as erro:
            print(f"  lote {inicio // 12 + 1}: {erro}")
            continue
        for corte in (resposta.get("scripts") or []):
            if not isinstance(corte, dict) or not corte.get("script"):
                continue
            nome = str(corte.get("url", "")).rstrip("/").split("/")[-1] or f"corte{guardados}"
            (destino / f"{nome}.json").write_text(
                json.dumps(corte, ensure_ascii=False), encoding="utf-8"
            )
            guardados += 1
    print(f"\n  {guardados} corte(s) publicado(s) guardado(s) em {destino}\n")


def main():
    parser = argparse.ArgumentParser(description="Compara o corte do Furia com o que foi publicado.")
    parser.add_argument("--baixar", nargs="?", type=int, const=50, metavar="N",
                        help="traz N cortes publicados do CHUB (padrão 50)")
    parser.add_argument("--material", help="mede o Furia noutro material")
    parser.add_argument("--json", action="store_true", help="só os números")
    args = parser.parse_args()

    if args.baixar:
        baixar(args.baixar)
        return

    cortes = ler()
    publicados = medir(cortes)
    furia = furia_agora(args.material) if cortes else {"n": 0}

    if args.json:
        print(json.dumps({"publicados": publicados, "furia": furia}, ensure_ascii=False, indent=2))
    else:
        imprimir(publicados, furia)


if __name__ == "__main__":
    main()
