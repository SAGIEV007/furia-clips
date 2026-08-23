#!/usr/bin/env python3
"""Mede os cortes do Furia contra as fronteiras que um humano marcou.

A régua do NORTE §5 é a fonte real, não a suíte. E a §15 diz por que: um número
que a ferramenta produz sobre material que a ferramenta gerou não mede nada. A
referência aqui vem de fora — os blocos QA-gated do Acervo, rotulados por pessoa,
com a pergunta que disparou cada um e quantos cortes cabem dentro.

Um bloco do Acervo **não é um corte**: é um território de assunto de quatro a
oito minutos, e o campo `possibleCuts` diz quantos cortes o rotulador enxerga
dentro dele. Então IoU direto entre corte e bloco não quer dizer nada, e as três
medidas que querem são:

- **cobertura** — quantos territórios receberam ao menos um corte. Mede se o
  Furia varre a fonte ou se concentra num pedaço.
- **atravessamento** — quantos cortes cruzam uma fronteira de assunto. Um corte
  que começa num tema e termina noutro é o defeito que o editor chama de "não dá
  contexto".
- **duração** — a mediana do Furia contra a duração implícita do humano
  (território ÷ possibleCuts). É aqui que mora "parece não concluir o tema".

Uso:
    python scripts/medir_cortes.py [fixture.json ...]

Sem argumentos, roda em tudo que houver em tests/fixtures/acervo_*.json.
"""

from __future__ import annotations

import glob
import inspect
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.clip_selector import ClipSelector  # noqa: E402
from modules.editorial_context import analyze_transcript_context  # noqa: E402

TOQUE_MINIMO_S = 1.0
COBERTURA_MINIMA_S = 5.0


def cortar(segmentos, *, max_clips=12, min_duration=20, max_duration=480):
    seletor = ClipSelector(max_clips=max_clips, min_duration=min_duration, max_duration=max_duration)
    contexto = analyze_transcript_context({"segments": segmentos})
    aceitos = inspect.signature(seletor.select_clips).parameters
    argumentos = {
        nome: valor for nome, valor in [
            ("transcription", {"segments": segmentos}), ("energy_profile", []),
            ("user_context", ""), ("settings", {}), ("emit_progress", None),
            ("editorial_context", contexto),
        ] if nome in aceitos
    }
    return seletor, seletor.select_clips(**argumentos)


def medir(caminho: str) -> dict:
    fixture = json.loads(Path(caminho).read_text(encoding="utf-8"))
    segmentos = [
        {"start": s["start"], "end": s["end"], "text": s["text"]}
        for s in fixture["sentencas"]
    ]
    territorios = [(r["start"], r["end"], r["cortes"]) for r in fixture["blocos_de_referencia"]]
    seletor, clips = cortar(segmentos)
    blocos = seletor._build_transcript_blocks(seletor._build_sentences(segmentos))

    def tocados(clip):
        return [
            t for t in territorios
            if min(t[1], clip["end"]) - max(t[0], clip["start"]) > TOQUE_MINIMO_S
        ]

    atravessam = [c for c in clips if len(tocados(c)) > 1]
    cobertos = [
        t for t in territorios
        if any(min(t[1], c["end"]) - max(t[0], c["start"]) > COBERTURA_MINIMA_S for c in clips)
    ]
    duracoes = sorted(c["end"] - c["start"] for c in clips) or [0.0]
    alvo = [(t[1] - t[0]) / max(1, t[2]) for t in territorios] or [0.0]

    return {
        "fonte": fixture["fonte"]["titulo"],
        "video": fixture["fonte"]["videoId"],
        "janela_s": fixture["janela"]["ate_s"] - fixture["janela"]["de_s"],
        "territorios": len(territorios),
        "cortes_esperados": sum(t[2] for t in territorios),
        "blocos": len(blocos),
        "bloco_mediano_s": round(statistics.median(b["duration"] for b in blocos), 1) if blocos else 0.0,
        "cortes": len(clips),
        "cobertura": f"{len(cobertos)}/{len(territorios)}",
        "atravessam": len(atravessam),
        "atravessam_pct": round(100 * len(atravessam) / len(clips)) if clips else 0,
        "duracao_mediana_s": round(statistics.median(duracoes), 1),
        "duracao_alvo_s": round(statistics.median(alvo), 1),
        "razao_duracao": round(statistics.median(duracoes) / statistics.median(alvo), 2) if alvo else 0.0,
    }


def main(caminhos):
    if not caminhos:
        raiz = Path(__file__).resolve().parent.parent
        caminhos = sorted(glob.glob(str(raiz / "tests" / "fixtures" / "acervo_*.json")))
    if not caminhos:
        print("nenhuma fixture do Acervo encontrada em tests/fixtures/")
        return 1

    linhas = [medir(caminho) for caminho in caminhos]
    largura = 118
    print("=" * largura)
    print("CORTES DO FURIA CONTRA AS FRONTEIRAS MARCADAS POR HUMANO (Acervo)")
    print("=" * largura)
    for linha in linhas:
        print(f"\n{linha['fonte'][:96]}")
        print(f"  {linha['video']} · janela {linha['janela_s']:.0f}s · {linha['territorios']} territórios de assunto")
        print(f"  blocos do Furia ....... {linha['blocos']:4}  (mediana {linha['bloco_mediano_s']:6.1f}s)")
        print(f"  cortes ................ {linha['cortes']:4}  (o humano vê {linha['cortes_esperados']})")
        print(f"  cobertura ............. {linha['cobertura']:>4}  territórios com ao menos um corte")
        print(f"  atravessam fronteira .. {linha['atravessam']:4}  ({linha['atravessam_pct']}%)")
        print(f"  duração mediana ....... {linha['duracao_mediana_s']:6.1f}s  alvo humano {linha['duracao_alvo_s']:6.1f}s"
              f"  →  razão {linha['razao_duracao']}")

    if len(linhas) > 1:
        print("\n" + "-" * largura)
        print(f"AGREGADO em {len(linhas)} fontes:")
        print(f"  razão de duração (mediana) .. {statistics.median(l['razao_duracao'] for l in linhas):.2f}"
              "   (1.0 = do tamanho que o humano implica)")
        print(f"  atravessamento (mediana) .... {statistics.median(l['atravessam_pct'] for l in linhas):.0f}%")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
