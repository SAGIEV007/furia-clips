"""Mede CONTEXTO — se o corte se sustenta sozinho.

Prioridade declarada pelo Fernando (01/09): *"essa duracao e legal mas a parte
de contexto e imprescindivel"*. Um corte de 117s que abre no meio do raciocinio
e pior que um de 60s que se explica sozinho.

O acervo do Chub ja tem esse julgamento: `self_contained_rank` (percentil de
auto-suficiencia) e `needs_context` (depende do que veio antes). Os blocos de
nota alta seguem um padrao claro, visivel em `self_contained_reason`:

  "O bloco apresenta a pergunta, explica o conceito, fornece exemplos legais e
   explicita a proposta e o prazo."

Ou seja: PERGUNTA + RESPOSTA + FECHAMENTO na mesma janela. E isso que este
script mede, em vez de so sobreposicao temporal.

Uso:
    python scripts/bench_contexto.py
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


def bloco_mais_proximo(clip, gabarito):
    melhor, score = None, 0.0
    for bloco in gabarito:
        s = iou(clip["start"], clip["end"], bloco["start_s"], bloco["end_s"])
        if s > score:
            melhor, score = bloco, s
    return melhor, score


def avaliar(rotulo, settings=None):
    from modules.clip_selector import ClipSelector

    dados = json.load(io.open(TRANSCRICAO, encoding="utf-8"))
    gabarito = json.load(io.open(GABARITO, encoding="utf-8"))

    seletor = ClipSelector()
    clips = seletor.select_clips(dados, settings=settings) if settings else seletor.select_clips(dados)

    aprovados = []
    for clip in clips:
        veredito, _ = seletor.quality_gate(clip)
        if veredito in ("accept", "approve", "review"):
            aprovados.append(clip)

    if not aprovados:
        print(f"{rotulo}: nenhum corte aprovado")
        return

    # 1. O corte abre onde o assunto abre?
    abre_no_lugar = 0
    # 2. Fecha onde o assunto fecha?
    fecha_no_lugar = 0
    # 3. Herda um bloco auto-suficiente (o acervo diz que se sustenta)?
    autossuficientes = 0
    # 4. Cai em bloco que o proprio acervo marca como dependente de contexto?
    dependentes = 0
    # 5. Flags editoriais internos do Furia
    com_contexto = sum(1 for c in aprovados if c.get("context_complete"))
    com_fecho = sum(1 for c in aprovados if c.get("payoff_complete"))
    abre_no_meio = sum(1 for c in aprovados if c.get("starts_mid_sentence"))
    referencia_solta = sum(1 for c in aprovados if c.get("starts_with_context_reference"))

    for clip in aprovados:
        bloco, score = bloco_mais_proximo(clip, gabarito)
        if not bloco:
            continue
        # tolerancia de 3s: abrir/fechar junto com a fronteira do bloco
        if abs(clip["start"] - bloco["start_s"]) <= 3.0:
            abre_no_lugar += 1
        if abs(clip["end"] - bloco["end_s"]) <= 3.0:
            fecha_no_lugar += 1
        if int(bloco.get("self_contained_rank") or 0) >= 70:
            autossuficientes += 1
        if bloco.get("needs_context"):
            dependentes += 1

    n = len(aprovados)
    pct = lambda x: f"{100*x/n:.0f}%"

    print(f"\n=== {rotulo} ({n} cortes) ===")
    print("  FRONTEIRA (vs. acervo)")
    print(f"    abre junto com o bloco .......... {abre_no_lugar}/{n}  {pct(abre_no_lugar)}")
    print(f"    fecha junto com o bloco ......... {fecha_no_lugar}/{n}  {pct(fecha_no_lugar)}")
    print("  AUTO-SUFICIENCIA (julgamento do acervo)")
    print(f"    herda bloco que se sustenta ..... {autossuficientes}/{n}  {pct(autossuficientes)}")
    print(f"    cai em bloco dependente ......... {dependentes}/{n}  {pct(dependentes)}  <- quanto menor, melhor")
    print("  FLAGS EDITORIAIS (julgamento do Furia)")
    print(f"    contexto completo ............... {com_contexto}/{n}  {pct(com_contexto)}")
    print(f"    fecho completo .................. {com_fecho}/{n}  {pct(com_fecho)}")
    print(f"    abre no meio da frase ........... {abre_no_meio}/{n}  {pct(abre_no_meio)}  <- quanto menor, melhor")
    print(f"    abre com referencia solta ....... {referencia_solta}/{n}  {pct(referencia_solta)}  <- quanto menor, melhor")


if __name__ == "__main__":
    print("CONTEXTO acima de duracao — 63 blocos do Garimpo como referencia")
    avaliar("SEM acervo")
    snapshot = json.load(io.open(SNAPSHOT, encoding="utf-8"))
    avaliar("COM acervo", settings={"campaign_hub_snapshot": snapshot})
