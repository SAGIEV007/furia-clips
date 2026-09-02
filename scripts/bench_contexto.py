import json, io, sys

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


def ultimo_segmento(intervalo_start, intervalo_end, segs, tol=0.5):
    candidatos = [s for s in segs if s["end"] <= intervalo_end + tol and s["start"] >= intervalo_start - tol]
    if not candidatos:
        candidatos = [s for s in segs if s["end"] <= intervalo_end + tol]
    if not candidatos:
        return None
    return max(candidatos, key=lambda s: s["end"])


def classificar_borda_saida(texto):
    t = texto.rstrip()
    if t.endswith(".") or t.endswith("!"):
        return "ponto_exclamacao"
    elif t.endswith("?"):
        return "pergunta"
    elif t.endswith(","):
        return "virgula"
    else:
        return "sem_pontuacao"


def avaliar(rotulo, settings=None):
    from modules.clip_selector import ClipSelector

    dados = json.load(io.open(TRANSCRICAO, encoding="utf-8"))
    gabarito = json.load(io.open(GABARITO, encoding="utf-8"))
    segs = dados["segments"]

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

    abre_no_lugar = 0
    fecha_no_lugar = 0
    autossuficientes = 0
    dependentes = 0
    com_contexto = sum(1 for c in aprovados if c.get("context_complete"))
    com_fecho = sum(1 for c in aprovados if c.get("payoff_complete"))
    abre_no_meio = sum(1 for c in aprovados if c.get("starts_mid_sentence"))
    referencia_solta = sum(1 for c in aprovados if c.get("starts_with_context_reference"))

    # P4: borda de saida (5 categorias da pesquisa)
    borda_categorias = {
        "ponto_exclamacao": 0,
        "pergunta": 0,
        "virgula": 0,
        "sem_pontuacao": 0,
        "sem_segmento": 0,
    }
    gabarito_borda = {
        "ponto_exclamacao": 0,
        "pergunta": 0,
        "virgula": 0,
        "sem_pontuacao": 0,
        "sem_segmento": 0,
    }
    for b in gabarito:
        s = ultimo_segmento(b["start_s"], b["end_s"], segs)
        if s:
            cat = classificar_borda_saida(s["text"])
        else:
            cat = "sem_segmento"
        gabarito_borda[cat] = gabarito_borda.get(cat, 0) + 1

    for clip in aprovados:
        bloco, score = bloco_mais_proximo(clip, gabarito)
        if not bloco:
            continue
        if abs(clip["start"] - bloco["start_s"]) <= 3.0:
            abre_no_lugar += 1
        if abs(clip["end"] - bloco["end_s"]) <= 3.0:
            fecha_no_lugar += 1
        if int(bloco.get("self_contained_rank") or 0) >= 70:
            autossuficientes += 1
        if bloco.get("needs_context"):
            dependentes += 1

        s = ultimo_segmento(clip["start"], clip["end"], segs)
        if s:
            cat = classificar_borda_saida(s["text"])
        else:
            cat = "sem_segmento"
        borda_categorias[cat] = borda_categorias.get(cat, 0) + 1

    n = len(aprovados)
    pct = lambda x: f"{100*x/n:.0f}%"
    g_n = len(gabarito)
    g_pct = lambda x: f"{100*x/g_n:.0f}%"

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
    print("  BORDA DE SAIDA (ultima frase do corte vs. gabarito)")
    print(f"    . ou ! (ideal) .................. {borda_categorias['ponto_exclamacao']}/{n}  {pct(borda_categorias['ponto_exclamacao'])}")
    print(f"    ? ................................ {borda_categorias['pergunta']}/{n}  {pct(borda_categorias['pergunta'])}")
    print(f"    , ................................ {borda_categorias['virgula']}/{n}  {pct(borda_categorias['virgula'])}")
    print(f"    sem pontuacao .................... {borda_categorias['sem_pontuacao']}/{n}  {pct(borda_categorias['sem_pontuacao'])}")
    print(f"    (gabarito ref: .! {gabarito_borda['ponto_exclamacao']}/{g_n} {g_pct(gabarito_borda['ponto_exclamacao'])}, ? {gabarito_borda['pergunta']}/{g_n} {g_pct(gabarito_borda['pergunta'])}, , {gabarito_borda['virgula']}/{g_n} {g_pct(gabarito_borda['virgula'])}, sem {gabarito_borda['sem_pontuacao']}/{g_n} {g_pct(gabarito_borda['sem_pontuacao'])})")


if __name__ == "__main__":
    print("CONTEXTO acima de duracao — 63 blocos do Garimpo como referencia")
    avaliar("SEM acervo")
    snapshot = json.load(io.open(SNAPSHOT, encoding="utf-8"))
    avaliar("COM acervo", settings={"campaign_hub_snapshot": snapshot})
