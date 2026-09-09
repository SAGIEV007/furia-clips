#!/usr/bin/env python3
"""Quantas viradas de assunto o Furia enxerga sozinho.

A PERGUNTA DO EDITOR QUE ORIGINOU ISTO
--------------------------------------
    "o fúria não deveria estar SEMPRE usando o chub? (...) porque não usou e
     acertou 10 de 10?"

A resposta está aqui, e é desconfortável: **num vídeo do Acervo, a leitura
própria do Furia quase não é usada — os blocos revisados cobrem a falha. Na live
de ontem não há o que cobrir.**

Esta régua mede a leitura própria contra a do Acervo, no mesmo vídeo. Não é o
mesmo que `regua.py`: aquela mede onde os CORTES caem; esta mede se o programa
sequer SABE onde um assunto acaba e outro começa.

Medido em 07/09 na sabatina: 8 assuntos contra 10, e **1 das 9 viradas achada**.

O CUIDADO QUE VALE MAIS QUE O NÚMERO
------------------------------------
Não usar a borda do Acervo para cortar e depois medir contra a borda do Acervo.
O gabarito não pode ser a entrada: o número subiria sem o corte melhorar, e a
régua estaria conferindo a própria cola.

USO
---
    python scripts/regua_assuntos.py
    python scripts/regua_assuntos.py --material tests/fixtures/acervo_xxx.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Quanto uma virada pode errar e ainda contar como achada. Quinze segundos é
# generoso de propósito: o objetivo é saber se o programa VIU a virada, não se
# acertou o segundo.
TOLERANCIA_S = 15.0


def medir(material: str = "", *, pelo_modelo: bool = False):
    """As fronteiras que o Furia vê, pelo caminho que ele usaria de verdade.

    `pelo_modelo` mede o caminho que manda o vídeo INTEIRO numerado ao Gemini e
    recebe as fronteiras pelo número da frase — a receita do CHUB. Precisa de
    chave configurada, e por isso não roda na bancada offline: o número dele só
    existe na máquina do editor. Sem a bandeira, mede a leitura local por
    coesão, que é a que roda sem internet.
    """
    from modules.clip_selector import ClipSelector
    from scripts.regua import carregar_material

    transcricao, blocos, fonte, quem = carregar_material(material or None)
    seletor = ClipSelector(min_duration=15, max_duration=180, max_clips=12)
    # As frases como o MOTOR as constrói, não as do arquivo: a diferença entre
    # as duas já mudou o resultado uma vez.
    frases = seletor._build_sentences(transcricao["segments"])
    if pelo_modelo:
        from database import get_all_settings

        seletor._settings_da_moagem = get_all_settings()
    else:
        seletor._settings_da_moagem = {}
    seletor._candidate_diagnostics = {}
    # O MESMO caminho que a moagem usa, não uma cópia dele. Medir uma cópia foi
    # como quatro defeitos desta semana passaram pelos testes.
    unidades = seletor._assuntos_do_video(frases)

    bordas_gabarito = [float(b["start"]) for b in blocos[1:]]
    bordas_furia = [float(u["start_s"]) for u in unidades[1:]]
    return fonte, quem, blocos, unidades, bordas_gabarito, bordas_furia


def main():
    parser = argparse.ArgumentParser(description="Mede se o Furia enxerga as viradas de assunto.")
    parser.add_argument("--material", help="outro material com gabarito")
    parser.add_argument("--pelo-modelo", action="store_true",
                        help="medir o caminho que pergunta ao Gemini pelo número da frase")
    args = parser.parse_args()

    fonte, quem, blocos, unidades, gabarito, furia = medir(
        args.material, pelo_modelo=args.pelo_modelo)

    print()
    print(f"  material: {fonte.get('titulo', '')[:52]}")
    print(f"  {quem} divide em {len(blocos)} assuntos · o Furia lê {len(unidades)}")
    print()
    if not gabarito:
        print("  O gabarito tem um assunto só; não há virada para conferir.")
        print()
        return

    print(f"  {'gabarito':>10}   o mais próximo que o Furia viu")
    achadas = 0
    for borda in gabarito:
        if furia:
            perto = min(furia, key=lambda f: abs(f - borda))
            erro = abs(perto - borda)
        else:
            perto, erro = 0.0, 9e9
        marca = "ACHOU" if erro <= TOLERANCIA_S else ""
        achadas += 1 if erro <= TOLERANCIA_S else 0
        print(f"  {borda:10.1f}   ->  {perto:8.1f}   ({erro:6.1f}s)  {marca}")
    # Quantas das fronteiras que o Furia PROPÔS são reais. Sem este número,
    # "achadas" se conserta propondo mais: quem chuta uma virada a cada dez
    # segundos acha todas e não sabe nada. Foi o que quase aconteceu aqui — uma
    # mudança levou "achadas" de 1/9 a 3/9 e o total de fronteiras de 7 a 20,
    # com a precisão parada em 14%.
    certeiras = sum(
        1 for f in furia if gabarito and min(abs(f - b) for b in gabarito) <= TOLERANCIA_S
    )
    print()
    print(f"    viradas de assunto achadas .... {achadas:3}/{len(gabarito)}"
          f"  {100 * achadas / len(gabarito):5.0f}%   subir")
    print(f"    fronteiras propostas certeiras  {certeiras:3}/{len(furia) or 1}"
          f"  {100 * certeiras / max(1, len(furia)):5.0f}%   subir   (anti-chute)")
    print(f"    maior pedaço que o Furia vê ... {max(u['duration_s'] for u in unidades):8.0f}s")
    print(f"    maior bloco do gabarito ....... "
          f"{max(float(b['end']) - float(b['start']) for b in blocos):8.0f}s")
    print()
    print("  Num vídeo catalogado esta falha fica escondida: os blocos revisados")
    print("  cobrem. Na live de ontem não há o que cobrir — por isso este número")
    print("  é a raiz, e não um detalhe.")
    print()


if __name__ == "__main__":
    main()
