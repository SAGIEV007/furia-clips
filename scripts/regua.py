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
import itertools
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


def carregar_material(caminho=None):
    arquivo = Path(caminho) if caminho else FIXTURE
    if not arquivo.is_file():
        raise SystemExit(
            f"Gabarito não encontrado: {arquivo}\n"
            "Traga material novo com: python scripts/novo_material.py --sortear"
        )
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    frases = dados["sentencas"]
    blocos = dados["blocos_de_referencia"]
    transcricao = {
        "segments": [dict(f) for f in frases],
        "full_text": " ".join(f["text"] for f in frases),
    }
    # De quem é a resposta certa. O Acervo é catálogo supervisionado; os cortes
    # do editor são o julgamento dele. Os dois valem — são evidência de fora —
    # mas dizem coisas diferentes, e a tela não pode trocar um pelo outro.
    origem = str((dados.get("proveniencia") or {}).get("origem") or "acervo_chub")
    quem = "você" if origem == "cortes_do_editor" else "o Acervo"
    return transcricao, blocos, dados.get("fonte", {}), quem


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
    """Os números de fora: onde o corte cai em relação ao gabarito do Acervo.

    CUIDADO COM O QUE SE PEDE. A primeira versão desta função media "quantos
    cortes fecham junto com o bloco" sobre o total de cortes — e isso é
    impossível de acertar. O Acervo diz que num bloco de 368 s cabem QUATRO
    cortes; só o primeiro pode abrir no início dele e só o último pode fechar no
    fim. Pedir que onze cortes fechem em dez bordas é pedir o impossível, e um
    agente otimizando sete horas contra um alvo impossível conclui que tudo
    falhou — ou descobre como trapacear.

    A trapaça, aqui, seria óbvia: um corte único de 137 segundos cobrindo o
    bloco 1 inteiro marcaria abertura e fecho perfeitos e seria um clipe
    inútil. Por isso `blocos engolidos` existe: ele denuncia exatamente essa
    saída.

    Todo número aqui é alcançável de verdade, e nenhum deles melhora ao entregar
    cortes piores.
    """
    n = len(entregues)
    total_esperado = sum(int(b.get("cortes") or 0) for b in blocos)

    def cruza(inicio, fim):
        """O corte pisa em dois assuntos diferentes."""
        for bloco in blocos:
            b_inicio, b_fim = float(bloco["start"]), float(bloco["end"])
            # Começa dentro deste bloco e termina depois do fim dele.
            if b_inicio - TOLERANCIA_S <= inicio < b_fim - TOLERANCIA_S and fim > b_fim + TOLERANCIA_S:
                return True
        return False

    alcancados = {}
    atravessam = 0
    for corte in entregues:
        inicio = float(corte.get("start", 0) or 0)
        fim = float(corte.get("end", 0) or 0)
        if cruza(inicio, fim):
            atravessam += 1
        for indice, bloco in enumerate(blocos):
            if inicio < float(bloco["end"]) and fim > float(bloco["start"]):
                alcancados.setdefault(indice, []).append((inicio, fim))

    # Dos blocos que receberam corte, em quantos algum corte abre junto com o
    # começo do assunto. Medido sobre blocos alcançados, não sobre cortes:
    # assim o alvo é alcançável.
    ancorados = 0
    engolidos = 0
    for indice, cortes_do_bloco in alcancados.items():
        bloco = blocos[indice]
        b_inicio, b_fim = float(bloco["start"]), float(bloco["end"])
        if any(abs(i - b_inicio) <= TOLERANCIA_S for i, _f in cortes_do_bloco):
            ancorados += 1
        # Bloco engolido: um corte só, cobrindo quase o bloco inteiro, num
        # bloco onde o Acervo diz que cabem vários. É a trapaça.
        if len(cortes_do_bloco) == 1 and int(bloco.get("cortes") or 1) > 1:
            i, f = cortes_do_bloco[0]
            if (min(f, b_fim) - max(i, b_inicio)) / max(1.0, b_fim - b_inicio) > 0.70:
                engolidos += 1

    ordenados = sorted(entregues, key=lambda c: float(c.get("start", 0) or 0))
    pior_repeticao = 0.0
    for antes, depois in itertools.pairwise(ordenados):
        comum = float(antes.get("end", 0) or 0) - float(depois.get("start", 0) or 0)
        if comum <= 0:
            continue
        duracao = max(1.0, float(depois.get("end", 0) or 0) - float(depois.get("start", 0) or 0))
        pior_repeticao = max(pior_repeticao, comum / duracao)

    return {
        "cortes": n,
        "cortes_esperados": total_esperado,
        "blocos_alcancados": len(alcancados),
        "blocos_total": len(blocos),
        "aberturas_ancoradas": ancorados,
        "atravessam_assunto": atravessam,
        "blocos_engolidos": engolidos,
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


def imprimir(fonte, fora, dentro, adiados, quem=""):
    n = max(1, fora["cortes"])
    b = max(1, fora["blocos_total"])
    alc = max(1, fora["blocos_alcancados"])

    print()
    print(f"  material: {fonte.get('titulo', 'sabatina')}  ({fonte.get('duracao_total_s', 0):.0f}s)")
    # Quem escreveu o gabarito muda o que a tela pode afirmar. Chamar de
    # "Acervo" um gabarito que o editor fez à mão apagaria a única coisa que
    # ele precisa saber para julgar o número: de quem é a resposta certa.
    print(f"  entregues: {fora['cortes']} cortes   ·   adiados pelo portão: {len(adiados)}"
          f"   ·   {quem} diz que cabem {fora['cortes_esperados']}")
    print()
    print(f"  ┌─ VERDADE DE FORA (contra {'os cortes que VOCÊ fez' if quem == 'você' else 'os blocos do Acervo'}) ─ ESTA É A META ─┐")
    print(f"     assuntos alcançados ........... {fora['blocos_alcancados']:3}/{fora['blocos_total']:<3}"
          f" {100 * fora['blocos_alcancados'] / b:5.0f}%   subir")
    print(f"     abre junto com o assunto ...... {fora['aberturas_ancoradas']:3}/{fora['blocos_alcancados']:<3}"
          f" {100 * fora['aberturas_ancoradas'] / alc:5.0f}%   subir   (dos blocos alcançados)")
    print(f"     atravessa dois assuntos ....... {fora['atravessam_assunto']:3}/{n:<3}"
          f" {100 * fora['atravessam_assunto'] / n:5.0f}%   baixar")
    print(f"     pior repetição entre cortes ... {fora['pior_repeticao']:>10}%   baixar")
    print(f"     blocos engolidos por um corte . {fora['blocos_engolidos']:>10}    baixar   (guarda anti-trapaça)")
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
    parser.add_argument("--material", metavar="ARQUIVO",
                        help="mede outro material (padrão: a sabatina da Band). "
                             "Traga mais com scripts/novo_material.py")
    parser.add_argument("--json", action="store_true", help="devolve só os números, para o agente ler")
    parser.add_argument("--salvar", metavar="ROTULO",
                        help="acrescenta a medição ao histórico com este rótulo")
    args = parser.parse_args()

    transcricao, blocos, fonte, quem = carregar_material(args.material)
    _candidatos, entregues, adiados = moer(transcricao)
    fora = medir(entregues, blocos)
    dentro = diagnosticar(entregues)

    if args.json:
        print(json.dumps({"fora": fora, "diagnostico": dentro, "adiados": len(adiados)},
                         ensure_ascii=False, indent=2))
    else:
        imprimir(fonte, fora, dentro, adiados, quem)

    if args.salvar:
        HISTORICO.parent.mkdir(parents=True, exist_ok=True)
        n = max(1, fora["cortes"])
        alc = max(1, fora["blocos_alcancados"])
        # Hora do relógio da máquina, de propósito: quem lê este histórico é
        # gente conferindo o que rodou de madrugada, e UTC já confundiu antes.
        linha = (
            f"{datetime.now().isoformat(timespec='seconds')} | {args.salvar} | "  # noqa: DTZ005
            f"{fonte.get('videoId', 'sabatina')} | "
            f"blocos {fora['blocos_alcancados']}/{fora['blocos_total']} | "
            f"ancorados {100 * fora['aberturas_ancoradas'] / alc:.0f}% | "
            f"atravessa {fora['atravessam_assunto']}/{n} | "
            f"repeticao {fora['pior_repeticao']}% | "
            f"engolidos {fora['blocos_engolidos']} | "
            f"cortes {fora['cortes']}\n"
        )
        with HISTORICO.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha)
        if not args.json:
            print(f"  guardado em {HISTORICO.relative_to(RAIZ)}")
            print()


if __name__ == "__main__":
    main()
