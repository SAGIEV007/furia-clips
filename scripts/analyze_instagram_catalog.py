from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [ROOT / "docs" / "instagram-api-catalog.csv", ROOT / "docs" / "instagram-full-catalog.csv"]
OUT_JSON = ROOT / "docs" / "instagram-catalog-metrics.json"
OUT_MD = ROOT / "docs" / "instagram-catalog-analysis.md"

input_path = next((path for path in INPUTS if path.exists() and path.stat().st_size > 0), INPUTS[0])
with input_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))


def number(value: str | None) -> float:
    if value in (None, "", "None"):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def keyword_hits(text: str, terms: tuple[str, ...]) -> int:
    normalized = text.lower()
    return sum(1 for term in terms if re.search(r"\b" + re.escape(term) + r"\b", normalized))


def row_metrics(row: dict[str, str]) -> dict[str, object]:
    views = number(row.get("video_view_count")) or number(row.get("play_count"))
    likes = number(row.get("like_count"))
    comments = number(row.get("comment_count"))
    followers = 0.0
    if row.get("profile") == "renansantosreserva":
        followers = 122683.0
    elif row.get("profile") == "renansantosmbl":
        followers = 2317169.0
    caption = row.get("caption", "")
    width = number(row.get("width"))
    height = number(row.get("height"))
    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "engagement_rate_by_views": (likes + comments) / views if views else 0.0,
        "view_rate_by_followers": views / followers if followers else 0.0,
        "aspect_ratio": width / height if width and height else 0.0,
        "caption_chars": len(caption),
        "caption_words": len(caption.split()),
        "signals": {
            "politics": keyword_hits(caption, ("política", "eleições", "governo", "presidente", "partido", "stf", "lula", "pt")),
            "conflict": keyword_hits(caption, ("ilegal", "destruiu", "violência", "traficantes", "jornalista", "investigar", "adversários", "sistema")),
            "humor": keyword_hits(caption, ("piada", "kkkk", "lá ele", "meme", "risada", "comédia")),
            "conclusion": keyword_hits(caption, ("afirma", "defende", "disse", "meta", "proposta", "recado", "mensagem", "não se cumpre")),
            "cta": keyword_hits(caption, ("siga", "concorda", "completem", "veja", "bora")),
        },
    }

metrics = []
for row in rows:
    metrics.append({**row, **row_metrics(row)})

by_profile: dict[str, list[dict[str, object]]] = defaultdict(list)
for row in metrics:
    by_profile[str(row["profile"])].append(row)

summary: dict[str, object] = {
    "source_file": str(input_path.relative_to(ROOT)),
    "rows": len(rows),
    "profiles": {},
    "limitations": [
        "O catálogo disponível ainda é uma amostra pública: 12 itens por perfil, com uma segunda resposta duplicada para reserva; a rota seguinte encontrou HTTP 429.",
        "Os campos de visualizações, curtidas e comentários são contagens observadas no momento da coleta e não são uma série temporal nem uma prova causal de viralidade.",
        "Não há duração, áudio, música, retenção, transcrição ou resultado audiovisual no catálogo de perfil; esses sinais precisam de análise do Reel individual.",
    ],
}

for profile, items in by_profile.items():
    views = [float(item["views"]) for item in items if float(item["views"]) > 0]
    rates = [float(item["engagement_rate_by_views"]) for item in items if float(item["views"]) > 0]
    top = sorted(items, key=lambda item: float(item["views"]), reverse=True)
    aspect_counts = Counter("vertical_9x16" if 0.52 <= float(item["aspect_ratio"]) <= 0.62 else "vertical_4x5" if 0.70 <= float(item["aspect_ratio"]) <= 0.82 else "square_or_other" for item in items)
    signal_counts = Counter()
    for item in items:
        signal_counts.update({name: value for name, value in dict(item["signals"]).items() if value})
    summary["profiles"][profile] = {
        "sample_size": len(items),
        "video_items": sum(1 for item in items if item.get("content_type") == "video"),
        "total_views_sample": sum(views),
        "median_views_sample": sorted(views)[len(views) // 2] if views else 0,
        "max_views_sample": max(views) if views else 0,
        "mean_engagement_rate_by_views": sum(rates) / len(rates) if rates else 0,
        "format_counts": dict(aspect_counts),
        "signal_counts": dict(signal_counts),
        "top_items_by_views": [
            {"shortcode": item.get("shortcode"), "views": item.get("views"), "likes": item.get("likes"), "comments": item.get("comments"), "caption": item.get("caption"), "url": item.get("url")} for item in top[:5]
        ],
    }

OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "# Análise do catálogo público do Instagram",
    "",
    f"**Arquivo de origem:** `{input_path.relative_to(ROOT)}`. A amostra contém **{len(rows)} linhas normalizadas**, com contagens públicas observadas para os dois perfis [5].",
    "",
    "> Esta versão distingue evidência observada de hipótese editorial. Ela não transforma curtidas ou visualizações em uma garantia de viralidade e não substitui a análise do vídeo individual.",
    "",
    "## Métricas observadas",
    "",
    "![Visualizações observadas por Reel](./instagram-catalog-views-log.png)",
    "",
    "| Perfil | Amostra | Vídeos | Visualizações na amostra | Mediana de visualizações | Máximo | Engajamento médio por visualização | Formato predominante |",
    "|---|---:|---:|---:|---:|---:|---:|---|",
]
for profile, data in summary["profiles"].items():
    formats = data["format_counts"]
    predominant = max(formats, key=formats.get) if formats else "n/d"
    lines.append(f"| `{profile}` | {data['sample_size']} | {data['video_items']} | {data['total_views_sample']:.0f} | {data['median_views_sample']:.0f} | {data['max_views_sample']:.0f} | {data['mean_engagement_rate_by_views']:.2%} | {predominant} |")

lines += [
    "",
    "## Padrões editoriais preliminares",
    "",
    "Na amostra disponível, os Reels combinam afirmação política direta, conflito com adversários ou instituições, reação a fatos noticiosos, humor/meme e chamadas para ação. Esses padrões foram observados nos itens públicos retornados pelos perfis [1] [2] e normalizados no catálogo local [5]. O perfil principal apresenta escala de visualizações muito superior à conta de reserva; por isso, o ranking do Furia Clips deve comparar cortes dentro de uma mesma live e normalizar sinais de audiência histórica, em vez de copiar limiares absolutos de um perfil para outro.",
    "",
    "Os formatos observados variam entre 9:16, 4:5 e quadrado. Para o produto, isso sustenta um enquadramento seguro com prioridade a 9:16, preservando margem para rosto, legendas futuras e elementos de interface; o sistema deve registrar o formato original e não cortar automaticamente uma fala importante para preencher a tela.",
    "",
    "A presença de legendas de publicação curtas, hashtags e CTAs sugere que o corte precisa entregar uma frase-âncora rapidamente, mas o catálogo não informa duração nem retenção. Consequentemente, a regra de seleção deve privilegiar contexto autossuficiente, progressão e payoff medidos na transcrição, deixando legenda visual e música como pós-produção.",
    "",
    "## Itens de maior alcance observados",
    "",
]
for profile, data in summary["profiles"].items():
    lines.append(f"### `{profile}`")
    lines.append("")
    lines.append("| Reel | Visualizações | Curtidas | Comentários | Leitura editorial pública |")
    lines.append("|---|---:|---:|---:|---|")
    for item in data["top_items_by_views"]:
        caption_text = str(item.get("caption", "")).replace("|", "\\|")[:180]
        lines.append(f"| [{item['shortcode']}]({item['url']}) | {float(item['views']):,.0f} | {float(item['likes']):,.0f} | {float(item['comments']):,.0f} | {caption_text} |")
    lines.append("")

lines += [
    "## Limitações e próximo nível de evidência",
    "",
    "A coleta integral está sujeita ao limite público do Instagram: a primeira página é acessível, mas as requisições seguintes sofreram HTTP 429, comportamento compatível com as limitações de automação descritas na documentação do extrator e em referências técnicas recentes [3] [4]. A tentativa via gallery-dl também não localizou os perfis sem autenticação. O coletor foi deixado retomável e registra cada página bruta [6]. Para cumprir literalmente a análise audiovisual de todos os Reels, seria necessário acesso autenticado ou uma exportação autorizada dos dados/mídias, além de tempo e capacidade de análise proporcionais a milhares de vídeos.",
    "",
    "A calibração do algoritmo nesta etapa deve ser tratada como **calibração inicial**, não como conclusão estatística. O próximo conjunto de dados prioritário é: duração, transcrição, início/fim do trecho, música/áudio, formato, presença de rosto e métricas de alcance por Reel. Com isso, será possível ajustar os gates de contexto e payoff com evidência audiovisual real.",
    "",
    "## Referências",
    "",
    "[1]: https://www.instagram.com/renansantosreserva/ — Perfil público @renansantosreserva.",
    "[2]: https://www.instagram.com/renansantosmbl/ — Perfil público @renansantosmbl.",
    "[3]: https://manpages.debian.org/unstable/gallery-dl/gallery-dl.conf.5.en.html — Documentação do gallery-dl 1.32.9.",
    "[4]: https://scrapfly.io/blog/posts/how-to-scrape-instagram — Referência técnica recente sobre endpoints públicos e limites de automação.",
    "[5]: ./instagram-api-catalog.csv — Catálogo normalizado salvo no repositório.",
    "[6]: ./instagram-full-collection.log — Log local da coleta paginada e dos checkpoints.",
]
OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
