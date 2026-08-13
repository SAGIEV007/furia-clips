from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs" / "instagram-api-catalog.csv"
OUT = ROOT / "docs" / "instagram-catalog-views-log.png"

with INPUT.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

for row in rows:
    row["views_num"] = float(row.get("video_view_count") or row.get("play_count") or 0)
rows.sort(key=lambda item: item["views_num"], reverse=True)
rows = rows[:15]
labels = [f"{row['profile'].replace('renansantos', '')}\n{row['shortcode']}" for row in rows]
values = [row["views_num"] for row in rows]
colors = ["#8b5cf6" if row["profile"] == "renansantosmbl" else "#0ea5e9" for row in rows]

plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(13, 7), dpi=180)
ax.bar(range(len(values)), values, color=colors)
ax.set_yscale("log")
ax.set_xticks(range(len(values)))
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Visualizações observadas (escala logarítmica)")
ax.set_title("Amostra pública inicial — visualizações por Reel")
ax.text(0.01, -0.23, "Amostra de 12 itens por perfil; contagens observadas no momento da coleta. Escala log não é previsão de viralidade.", transform=ax.transAxes, fontsize=9)
fig.tight_layout()
fig.savefig(OUT, bbox_inches="tight")
print(OUT)
