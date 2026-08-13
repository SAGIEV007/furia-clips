from pathlib import Path
import pandas as pd

base = Path(__file__).resolve().parents[1]
data = pd.read_csv(base / "docs/video-analysis/shorts_sample.csv")
summary = (
    data.groupby("editorial_type", as_index=False)
    .agg(
        videos=("id", "count"),
        median_views=("views", "median"),
        mean_views=("views", "mean"),
        max_views=("views", "max"),
    )
    .sort_values("median_views", ascending=False)
)
summary["median_views"] = summary["median_views"].round().astype(int)
summary["mean_views"] = summary["mean_views"].round().astype(int)
summary["max_views"] = summary["max_views"].astype(int)

report = [
    "# Comparação descritiva da amostra pública de Shorts",
    "",
    "A amostra não representa todo o canal e usa visualizações exibidas publicamente no momento da coleta. Ela serve para priorizar hipóteses editoriais, não para prever viralização.",
    "",
    "| Tipo editorial inicial | Vídeos | Mediana de visualizações | Média | Máximo |",
    "| --- | ---: | ---: | ---: | ---: |",
]
for row in summary.itertuples(index=False):
    report.append(
        f"| {row.editorial_type} | {row.videos} | {row.median_views:,} | {row.mean_views:,} | {row.max_views:,} |".replace(",", ".")
    )
report.extend([
    "",
    "## Leitura",
    "",
    "Na amostra coletada, os maiores valores aparecem em anúncios de consequência/campanha, respostas ou confrontos com alvo identificável, denúncias/choque e mobilização. Isso não prova causalidade: títulos, data de publicação, base de seguidores e assunto também influenciam o alcance.",
    "",
    "O sinal útil para o produto é combinar conflito ou consequência com especificidade, contexto e conclusão, em vez de pontuar apenas palavrões, exclamações ou polarização. O ranking deve também preservar diversidade entre confronto, proposta, evidência, posicionamento e mobilização.",
])
(base / "docs/video-analysis/shorts-sample-analysis.md").write_text("\n".join(report) + "\n", encoding="utf-8")
print(summary.to_string(index=False))
