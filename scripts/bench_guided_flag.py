"""Mede a regua do Garimpo com a ponte Chub ligada e desligada.

MOTIVO (medido 2026-09-01 21:0x, ciclo cron): a selecao guiada pelo Chub passou
a ser opt-in via `settings["campaign_hub_guided_selection"]`. Sem ninguem ligar
o flag, o ganho fica inerte em producao. Este script mede o delta real:

    COM Chub (flag OFF)  aprovados=15 (guiados=0) | IoU>=0.5: 40% | IoU>=0.3: 67%
    COM Chub (flag ON)   aprovados=15 (guiados=4) | IoU>=0.5: 47% | IoU>=0.3: 73%

Uso:
    python scripts/bench_guided_flag.py

Depende dos mesmos artefatos de `scripts/bench_vs_garimpo.py` (transcricao,
snapshot e gabarito em disco). Se algum faltar, o script avisa e sai sem erro.
"""
import io
import json
import os
import sys

sys.path.insert(0, ".")

from scripts.bench_vs_garimpo import GABARITO, SNAPSHOT, TRANSCRICAO, medir


def main():
    faltando = [p for p in (TRANSCRICAO, SNAPSHOT, GABARITO) if not os.path.exists(p)]
    if faltando:
        print("Artefato(s) ausente(s), nada a medir:")
        for p in faltando:
            print("  -", p)
        return 0

    snapshot = json.load(io.open(SNAPSHOT, encoding="utf-8"))
    print("Gabarito: 63 blocos do Garimpo | video o6yEVC-exk8 (Renan no SBT, 31 min)\n")
    medir("COM Chub (flag OFF)", settings={"campaign_hub_snapshot": snapshot})
    medir(
        "COM Chub (flag ON)",
        settings={
            "campaign_hub_snapshot": snapshot,
            "campaign_hub_guided_selection": True,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
