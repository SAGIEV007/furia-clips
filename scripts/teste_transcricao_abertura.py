#!/usr/bin/env python3
"""Mesmo motor, duas transcricoes: a manual (legenda YouTube) e a do Whisper.

Mede quantos cortes abrem no meio da frase em cada caso.
O medidor e validado contra casos conhecidos antes de rodar (licao 01/09:
medidor nao auditado ja produziu duas acusacoes falsas contra codigo bom).
"""
import json
import re
import sqlite3
import sys

sys.path.insert(0, ".")

DB = r"C:\Users\70156213125\FuriaClipsData\database\editorial_learning.sqlite3"
WHISPER = "FuriaClipsData/transcriptions/flow-news-065.json"
PROJECT_ID = 1490
OUT = "FuriaClipsData/calibration/teste-transcricao-abertura.json"


# ---------------------------------------------------------------- o medidor
def abre_limpo(texto_corte, texto_fonte):
    """True quando o corte comeca logo depois de um fim de frase na fonte.

    Nao usa lista de conectores (fragil). Usa a fonte: acha onde o texto do
    corte comeca e olha o caractere anterior.
    Retorna (bool, motivo).
    """
    corte = re.sub(r"\s+", " ", str(texto_corte or "")).strip()
    if not corte:
        return False, "corte vazio"
    chave = corte[:60]
    pos = texto_fonte.find(chave)
    if pos < 0:
        # fallback: tenta so as primeiras 6 palavras
        chave = " ".join(corte.split()[:6])
        pos = texto_fonte.find(chave)
        if pos < 0:
            return None, "nao localizado na fonte"
    if pos == 0:
        return True, "inicio da fonte"
    antes = texto_fonte[:pos].rstrip()
    if not antes:
        return True, "inicio da fonte"
    ultimo = antes[-1]
    if ultimo in ".!?":
        return True, f"fecho anterior '{ultimo}'"
    return False, f"anterior termina em '{ultimo}'"


def validar_medidor():
    """O medidor tem que acertar casos que eu sei a resposta."""
    fonte = "Primeira frase completa. E aqui comeca a segunda frase que segue."
    casos = [
        ("Primeira frase completa.", True, "abre no inicio"),
        ("E aqui comeca a segunda frase", True, "abre depois de ponto"),
        ("comeca a segunda frase que segue", False, "abre no meio"),
        ("frase que segue", False, "abre no meio"),
    ]
    falhas = []
    for texto, esperado, nome in casos:
        got, motivo = abre_limpo(texto, fonte)
        if got != esperado:
            falhas.append(f"  FALHOU [{nome}]: esperado {esperado}, veio {got} ({motivo})")
    if falhas:
        print("MEDIDOR REPROVADO:")
        print("\n".join(falhas))
        sys.exit(1)
    print("medidor validado: 4/4 casos conhecidos corretos\n")


# ------------------------------------------------------------ transcricoes
def carregar_manual():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT segments FROM transcriptions WHERE project_id = ? LIMIT 1", (PROJECT_ID,))
    segs = json.loads(cur.fetchone()[0])
    conn.close()
    norm = []
    for s in segs:
        norm.append({
            "start": float(s.get("start", 0) or 0),
            "end": float(s.get("end", 0) or 0),
            "text": str(s.get("text", "") or ""),
        })
    return {"language": "pt", "segments": norm}


def carregar_whisper():
    with open(WHISPER, encoding="utf-8") as f:
        d = json.load(f)
    norm = []
    for s in d["segments"]:
        norm.append({
            "start": float(s.get("start", 0) or 0),
            "end": float(s.get("end", 0) or 0),
            "text": str(s.get("text", "") or ""),
        })
    return {"language": "pt", "segments": norm}


def medir(nome, transcricao):
    from modules.clip_selector import ClipSelector

    segs = transcricao["segments"]
    com_ponto = sum(1 for s in segs if s["text"].strip().endswith((".", "!", "?")))
    fonte = re.sub(r"\s+", " ", " ".join(s["text"].strip() for s in segs))

    print(f"=== {nome} ===")
    print(f"  segmentos: {len(segs)}")
    print(f"  com pontuacao final: {com_ponto} ({com_ponto/len(segs)*100:.1f}%)")

    selector = ClipSelector()
    clips = selector.select_clips(transcricao)
    print(f"  cortes gerados: {len(clips)}")

    limpos = meio = indef = 0
    detalhes = []
    for i, c in enumerate(clips, 1):
        ok, motivo = abre_limpo(c.get("text", ""), fonte)
        if ok is None:
            indef += 1
        elif ok:
            limpos += 1
        else:
            meio += 1
        detalhes.append({
            "n": i,
            "start": round(float(c.get("start", 0) or 0), 1),
            "duration": round(float(c.get("duration", 0) or 0), 1),
            "abre_limpo": ok,
            "motivo": motivo,
            "primeiras_palavras": " ".join(str(c.get("text", "")).split()[:12]),
            "flag_motor_starts_mid": bool(c.get("starts_mid_sentence")),
            "flag_motor_context_complete": bool(c.get("context_complete")),
        })

    total = len(clips) or 1
    print(f"  abrem LIMPO:      {limpos}/{len(clips)} ({limpos/total*100:.0f}%)")
    print(f"  abrem NO MEIO:    {meio}/{len(clips)} ({meio/total*100:.0f}%)")
    if indef:
        print(f"  indeterminado:    {indef}")
    print()
    for d in detalhes[:6]:
        marca = "OK  " if d["abre_limpo"] else "MEIO"
        print(f"   {marca} #{d['n']:02d} [{d['start']:.0f}s] {d['primeiras_palavras']}")
    print()

    return {
        "nome": nome,
        "segmentos": len(segs),
        "pct_pontuacao": round(com_ponto / len(segs) * 100, 1),
        "cortes": len(clips),
        "abrem_limpo": limpos,
        "abrem_no_meio": meio,
        "indeterminado": indef,
        "detalhes": detalhes,
    }


if __name__ == "__main__":
    validar_medidor()
    resultado = {
        "manual": medir("TRANSCRICAO MANUAL (legenda YouTube)", carregar_manual()),
        "whisper": medir("TRANSCRICAO WHISPER (faster-whisper medium)", carregar_whisper()),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    m, w = resultado["manual"], resultado["whisper"]
    print("=" * 60)
    print("VEREDITO")
    print("=" * 60)
    for r in (m, w):
        tot = r["cortes"] or 1
        print(f"{r['nome'][:40]:42s} {r['abrem_no_meio']:3d}/{r['cortes']:3d} no meio "
              f"({r['abrem_no_meio']/tot*100:.0f}%)  | pontuacao fonte: {r['pct_pontuacao']}%")
    print(f"\nArquivo: {OUT}")
