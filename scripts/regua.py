#!/usr/bin/env python3
"""A régua: o corte do Furia medido contra material com gabarito.

POR QUE ELA EXISTE
------------------
O turno da noite precisa de um número que o Furia não possa fabricar. Sem isso,
um agente cortando por sete horas produz erro com confiança — que é exatamente o
medo que o editor descreveu:

    "não adianta eu pedir ele para ficar 7 horas cortando o mesmo vídeo e
     saírem os mesmos resultados errados"

O DESENHO VEM DO `bench_contexto.py` DA BRANCH furia-sync-portable
------------------------------------------------------------------
Aquele script já tinha a ideia certa, e a mais importante delas: separar na tela
o que o ACERVO diz do que o FURIA acha de si mesmo. Esta régua copia essa
disciplina.

O que ela muda é de onde vem o gabarito. O `bench_contexto.py` lê de pasta
temporária do Windows (`AppData/Local/Temp/...`). Pasta temporária some, e uma
régua que some no meio da noite é pior que régua nenhuma: o turno continua
rodando e passa a medir nada.

Esta lê `tests/fixtures/acervo_sabatina_band.json`, que está versionado no
próprio repositório: 382 frases da sabatina da Band e 10 blocos de referência do
Acervo, com início e fim. Não depende de máquina, de pasta temporária nem de
download. `python scripts/regua.py` e pronto.

O QUE CONTA E O QUE NÃO CONTA
-----------------------------
Os blocos vêm do Acervo, que é supervisionado por gente. Por isso valem: a
resposta certa não foi escrita pelo programa que está sendo medido.

Os números que o Furia dá para si mesmo aparecem embaixo, marcados, e servem
para ENTENDER o que aconteceu — nunca para provar que melhorou. Dá para levar
"contexto completo" a 100% num minuto afrouxando a regra que decide isso; o
corte não melhora, o programa só passa a se elogiar mais.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

FIXTURE = RAIZ / "tests" / "fixtures" / "acervo_sabatina_band.json"
HISTORICO = RAIZ / "docs" / "hermes" / "medicoes.txt"

# Quanto um corte pode errar a borda e ainda contar como "no lugar". Três
# segundos é o mesmo tolerado pelo bench_contexto.py — mantido igual para as
# duas réguas continuarem comparáveis.
TOLERANCIA_S = 3.0


def carregar_material():
    if not FIXTURE.is_file():
        raise SystemExit(f"Gabarito não encontrado: {FIXTURE}")
    dados = json.loads(FIXTURE.read_text(encoding="utf-8"))
    frases = dados["sentencas"]
    blocos = dados["blocos_de_referencia"]
    transcricao = {
        "segments": [dict(f) for f in frases],
        "full_text": " ".join(f["text"] for f in frases),
    }
    return transcricao, blocos, dados.get("fonte", {})


def moer(transcricao):
    """Roda o caminho completo: seletor, ranqueador e portão editorial."""
    import app as motor
    from modules.clip_selector import ClipSelector
    from modules.viral_ranker import ViralRanker

    seletor = ClipSelector(min_duration=15, max_duration=180, max_clips=12)
    candidatos = seletor.select_clips(
        transcricao,
        settings={"editorial_context": {}},
        emit_progress=lambda *_a, **_k: None,
    )
    ranqueados = ViralRanker(editorial_profile="renan_santos_politics").rank_clips(candidatos)
    entregues, adiados = motor._defer_context_incomplete_candidates(ranqueados)
    return candidatos, entregues, adiados


def medir(entregues, blocos):
    """Os números de fora: onde o corte cai em relação ao gabarito do Acervo."""
    n = len(entregues)
    abre_no_lugar = 0
    fecha_no_lugar = 0
    blocos_alcancados = set()

    for corte in entregues:
        inicio = float(corte.get("start", 0) or 0)
        fim = float(corte.get("end", 0) or 0)
        for indice, bloco in enumerate(blocos):
            b_inicio = float(bloco["start"])
            b_fim = float(bloco["end"])
            if abs(inicio - b_inicio) <= TOLERANCIA_S:
                abre_no_lugar += 1
                break
        for bloco in blocos:
            if abs(fim - float(bloco["end"])) <= TOLERANCIA_S:
                fecha_no_lugar += 1
                break
        # Um bloco é "alcançado" quando algum corte cai dentro dele. Mede se o
        # programa achou o material, mesmo tendo errado a borda.
        for indice, bloco in enumerate(blocos):
            if inicio < float(bloco["end"]) and fim > float(bloco["start"]):
                blocos_alcancados.add(indice)

    # Repetição: quanto de um corte já estava em outro. Dois cortes que dividem
    # metade do tempo são o mesmo clipe entregue duas vezes.
    ordenados = sorted(entregues, key=lambda c: float(c.get("start", 0) or 0))
    pior_repeticao = 0.0
    for antes, depois in zip(ordenados, ordenados[1:]):
        comum = float(antes.get("end", 0) or 0) - float(depois.get("start", 0) or 0)
        if comum <= 0:
            continue
        duracao = max(1.0, float(depois.get("end", 0) or 0) - float(depois.get("start", 0) or 0))
        pior_repeticao = max(pior_repeticao, comum / duracao)

    return {
        "cortes": n,
        "abre_no_lugar": abre_no_lugar,
        "fecha_no_lugar": fecha_no_lugar,
        "blocos_alcancados": len(blocos_alcancados),
        "blocos_total": len(blocos),
        "pior_repeticao": round(pior_repeticao * 100),
    }


def diagnosticar(entregues):
    """O que o Furia acha de si mesmo. Serve para entender, não para provar."""
    from modules.interview_turns import opens_without_a_claim

    n = max(1, len(entregues))
    abre_fora = 0
    for corte in entregues:
        primeira = str(corte.get("text") or "").strip().split(".")[0][:200]
        if opens_without_a_claim(primeira):
            abre_fora += 1
    return {
        "contexto_completo": sum(1 for c in entregues if c.get("context_complete")),
        "fecho_completo": sum(1 for c in entregues if c.get("payoff_complete")),
        "abre_no_meio": sum(1 for c in entregues if c.get("starts_mid_sentence")),
        "abre_fora_do_entrevistado": abre_fora,
        "n": n,
    }


def imprimir(fonte, fora, dentro, adiados):
    n = max(1, fora["cortes"])
    pct = lambda x: f"{100 * x / n:5.0f}%"

    print()
    print(f"  material: {fonte.get('titulo', 'sabatina')}  ({fonte.get('duracao_total_s', 0):.0f}s)")
    print(f"  entregues: {fora['cortes']} cortes   ·   adiados pelo portão: {len(adiados)}")
    print()
    print("  ┌─ VERDADE DE FORA (contra os blocos do Acervo) ─ ESTA É A META ─┐")
    print(f"     abre junto com o bloco ........ {fora['abre_no_lugar']:3}/{n:<3} {pct(fora['abre_no_lugar'])}   subir")
    print(f"     fecha junto com o bloco ....... {fora['fecha_no_lugar']:3}/{n:<3} {pct(fora['fecha_no_lugar'])}   subir")
    print(f"     blocos do Acervo alcançados ... {fora['blocos_alcancados']:3}/{fora['blocos_total']:<3}"
          f" {100 * fora['blocos_alcancados'] / max(1, fora['blocos_total']):5.0f}%   subir")
    print(f"     pior repetição entre cortes ... {fora['pior_repeticao']:>10}%   baixar")
    print("  └─────────────────────────────────────────────────────────────────┘")
    print()
    print("   diagnóstico — o Furia se avaliando. NÃO é meta; serve para entender:")
    print(f"     contexto completo ............. {dentro['contexto_completo']:3}/{n}")
    print(f"     fecho completo ................ {dentro['fecho_completo']:3}/{n}")
    print(f"     abre no meio da frase ......... {dentro['abre_no_meio']:3}/{n}")
    print(f"     abre fora do entrevistado ..... {dentro['abre_fora_do_entrevistado']:3}/{n}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Mede o corte do Furia contra o gabarito do Acervo.")
    parser.add_argument("--json", action="store_true", help="devolve só os números, para o agente ler")
    parser.add_argument("--salvar", metavar="ROTULO",
                        help="acrescenta a medição ao histórico com este rótulo")
    args = parser.parse_args()

    transcricao, blocos, fonte = carregar_material()
    candidatos, entregues, adiados = moer(transcricao)
    fora = medir(entregues, blocos)
    dentro = diagnosticar(entregues)

    if args.json:
        print(json.dumps({"fora": fora, "diagnostico": dentro, "adiados": len(adiados)},
                         ensure_ascii=False, indent=2))
    else:
        imprimir(fonte, fora, dentro, adiados)

    if args.salvar:
        HISTORICO.parent.mkdir(parents=True, exist_ok=True)
        n = max(1, fora["cortes"])
        linha = (
            f"{datetime.now().isoformat(timespec='seconds')} | {args.salvar} | "
            f"abre {100 * fora['abre_no_lugar'] / n:.0f}% | "
            f"fecha {100 * fora['fecha_no_lugar'] / n:.0f}% | "
            f"blocos {fora['blocos_alcancados']}/{fora['blocos_total']} | "
            f"repeticao {fora['pior_repeticao']}% | "
            f"cortes {fora['cortes']}\n"
        )
        with HISTORICO.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha)
        if not args.json:
            print(f"  guardado em {HISTORICO.relative_to(RAIZ)}")
            print()


if __name__ == "__main__":
    main()
