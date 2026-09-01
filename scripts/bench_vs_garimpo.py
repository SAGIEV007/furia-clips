"""Mede o Furia contra o gabarito do Garimpo/Chub.

Uso:
    python scripts/bench_vs_garimpo.py

Compara os cortes que o Furia produz com os blocos que o site Garimpo ja
interpretou para o mesmo video, usando IoU (sobreposicao temporal).

Este e o teste de regua do projeto: qualquer mudanca no motor deve ser medida
aqui, contra a interpretacao real do acervo, nao contra opiniao.
"""
import io
import json
import sys

sys.path.insert(0, ".")

TRANSCRICAO = r"C:/Users/70156213125/AppData/Local/Temp/bench_transcricao.json"
SNAPSHOT = r"C:/Users/70156213125/FuriaClipsData/campaign_hub/snapshot_o6yEVC.json"
GABARITO = r"C:/Users/70156213125/AppData/Local/Temp/gabarito_o6yEVC.json"


def iou(a0, a1, b0, b1):
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    uniao = max(a1, b1) - min(a0, b0)
    return inter / uniao if uniao > 0 else 0.0


def medir(rotulo, settings=None):
    from modules.clip_selector import ClipSelector

    dados = json.load(io.open(TRANSCRICAO, encoding="utf-8"))
    gabarito = json.load(io.open(GABARITO, encoding="utf-8"))

    seletor = ClipSelector()
    clips = seletor.select_clips(dados, settings=settings) if settings else seletor.select_clips(dados)

    aprovados = []
    for clip in clips:
        veredito, _motivo = seletor.quality_gate(clip)
        if veredito in ("accept", "approve", "review"):
            aprovados.append(clip)

    if not aprovados:
        print(f"{rotulo:<26} NENHUM CORTE APROVADO de {len(clips)} candidatos")
        return

    scores = []
    for clip in aprovados:
        melhor = 0.0
        for bloco in gabarito:
            s = iou(clip["start"], clip["end"], bloco["start_s"], bloco["end_s"])
            melhor = max(melhor, s)
        scores.append(melhor)

    duracoes = sorted(c["duration"] for c in aprovados)
    guiados = sum(1 for c in aprovados if c.get("campaign_hub"))
    n = len(scores)
    alto = sum(1 for s in scores if s >= 0.5)
    parcial = sum(1 for s in scores if s >= 0.3)

    print(
        f"{rotulo:<26} aprovados={n:>3} (guiados={guiados:>2}) | "
        f"IoU>=0.5: {alto}/{n} = {100*alto/n:.0f}% | "
        f"IoU>=0.3: {100*parcial/n:.0f}% | "
        f"mediana {duracoes[n//2]:.0f}s (alvo 117s)"
    )


if __name__ == "__main__":
    print("Gabarito: 63 blocos do Garimpo | video o6yEVC-exk8 (Renan no SBT, 31 min)\n")
    medir("SEM Chub (baseline)")
    snapshot = json.load(io.open(SNAPSHOT, encoding="utf-8"))
    medir("COM Chub (guiado)", settings={"campaign_hub_snapshot": snapshot})
