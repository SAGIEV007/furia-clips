#!/usr/bin/env python3
"""Diagnóstico completo dos cortes aprovados pelo Fúria."""
import json
from collections import Counter

CLIPS_PATH = "FuriaClipsData/calibration/clips-flow-065.json"
OUT_PATH = "FuriaClipsData/calibration/diagnostico-completo-flow-065.md"

GRADE_SCORE = {"A": 90, "B": 55, "C": 25}
WEIGHTS = {"hook": 0.20, "flow": 0.25, "value": 0.20, "audio": 0.35}

with open(CLIPS_PATH, "r", encoding="utf-8") as f:
    clips = json.load(f)

lines = []
lines.append("# Diagnóstico completo — Flow News #065\n")
lines.append(f"- Total de cortes: {len(clips)}\n")

# 1. Distribuição de editorial_gate_status
lines.append("## 1. Distribuição de editorial_gate_status\n")
statuses = Counter(tuple(c.get("editorial_gate_status", ["unknown"])) for c in clips)
for status, count in statuses.most_common():
    lines.append(f"- {status}: {count}\n")

# 2. Distribuição de grades
lines.append("\n## 2. Distribuição de grades (hook/flow/value/energy)\n")
for dim in ["hook", "flow", "value", "energy"]:
    grades = [c.get(dim, "B") for c in clips]
    dist = Counter(grades)
    lines.append(f"### {dim.upper()}")
    for grade in ["A", "B", "C"]:
        count = dist.get(grade, 0)
        lines.append(f"- {grade}: {count} ({count/len(clips)*100:.0f}%)\n")

# 3. Análise de viral_score
lines.append("\n## 3. Análise de viral_score\n")
scores = [c.get("viral_score", 0) for c in clips]
lines.append(f"- Min: {min(scores)}")
lines.append(f"- Max: {max(scores)}")
lines.append(f"- Média: {sum(scores)/len(scores):.1f}")
lines.append(f"- Cortes >= 50: {sum(1 for s in scores if s >= 50)}/{len(scores)}\n")

# 4. Recalcular viral_score por componente
lines.append("\n## 4. Componentes do viral_score por corte\n")
lines.append("| Corte | Start | Dur | hook | flow | value | energy | chub_mult | hook_dens | Calculado | Real | Diff |")
lines.append("|-------|-------|-----|------|------|-------|--------|-----------|-----------|-----------|------|------|")

for i, c in enumerate(clips, 1):
    hook = GRADE_SCORE.get(c.get("hook", "B"), 55)
    flow = GRADE_SCORE.get(c.get("flow", "B"), 55)
    value = GRADE_SCORE.get(c.get("value", "B"), 55)
    energy = GRADE_SCORE.get(c.get("energy", "B"), 55)
    chub_mult = c.get("chub_multiplier", 1.0)
    hook_dens = c.get("hook_density", 0.0)

    calculated = int((hook * chub_mult) * WEIGHTS["hook"] +
                     flow * WEIGHTS["flow"] +
                     value * WEIGHTS["value"] +
                     energy * WEIGHTS["audio"])

    # Aplicar penalidades
    penalized = calculated
    if hook_dens < 0.5:
        penalized -= 25
    elif hook_dens < 0.7:
        penalized -= 10
    if c.get("ceremonial_opening"):
        penalized -= 35
    penalized = max(0, min(100, penalized))

    real = c.get("viral_score", 0)
    diff = real - penalized

    lines.append(
        f"| {i} | {c.get('start', 0):.1f} | {c.get('duration', 0):.1f} "
        f"| {c.get('hook', 'B')} | {c.get('flow', 'B')} | {c.get('value', 'B')} "
        f"| {c.get('energy', 'B')} | {chub_mult:.2f} | {hook_dens:.2f} "
        f"| {calculated} | {real} | {diff} |"
    )

# 5. Análise de duração
lines.append("\n## 5. Análise de duração\n")
durations = [c.get("duration", 0) for c in clips]
lines.append(f"- Min: {min(durations):.1f}s")
lines.append(f"- Max: {max(durations):.1f}s")
lines.append(f"- Média: {sum(durations)/len(durations):.1f}s")
lines.append(f"- Cortes <= 45s: {sum(1 for d in durations if d <= 45)}")
lines.append(f"- Cortes 45-150s: {sum(1 for d in durations if 45 < d <= 150)}")
lines.append(f"- Cortes 150-180s: {sum(1 for d in durations if 150 < d <= 180)}")
lines.append(f"- Cortes > 180s: {sum(1 for d in durations if d > 180)}\n")

# 6. Textos dos cortes
lines.append("\n## 6. Textos dos cortes aprovados\n")
for i, c in enumerate(clips, 1):
    lines.append(f"### Corte {i}: {c.get('start', 0):.1f}s - {c.get('end', 0):.1f}s ({c.get('duration', 0):.1f}s)")
    lines.append(f"- Viral score: {c.get('viral_score', 0)}")
    lines.append(f"- Gate: {c.get('editorial_gate_status', [])}")
    lines.append(f"- Hook/Flow/Value/Energy: {c.get('hook', 'B')}/{c.get('flow', 'B')}/{c.get('value', 'B')}/{c.get('energy', 'B')}")
    lines.append(f"- Texto: {c.get('text', '')[:200]}...\n")

# 7. Diagnóstico
lines.append("\n## 7. Diagnóstico\n")
lines.append("TODO: Adicione aqui a análise dos componentes que mais penalizam.\n")
lines.append("Observações:")
lines.append("- Todos os cortes tem hook=flow=value=energy=B")
lines.append("- Calculado: 55, Real: 10-25, Diff: -30 a -45")
lines.append("- Possível causa: penalidades não capturadas pelo cálculo simples")
lines.append("- Próximo passo: verificar todas as penalidades no código\n")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Diagnóstico salvo em: {OUT_PATH}")
print(f"Total de cortes analisados: {len(clips)}")
print(f"\nDistribuição de editorial_gate_status:")
for status, count in statuses.most_common():
    print(f"  {status}: {count}")
