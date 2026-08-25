"""Aggregate Instagram editorial observations into a bounded ranking prior.

The detailed dataset is user-owned and lives outside the checkout. The packaged
fallback contains only aggregate family/layout statistics. This module never
uses raw URLs, captions, transcripts, or media as ranking input.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from statistics import mean, median
from typing import Any


LOCAL_DATASET_PATH = Path.home() / "FuriaClipsData" / "analyses" / "instagram-editorial-dataset-v1-2026-08-15.json"
PACKAGED_PRIORS_PATH = Path(__file__).resolve().parents[1] / "data" / "editorial_priors.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _observed_view_count(record: dict) -> float | None:
    """Return a real view count, never a fallback derived from other counters."""
    raw = record.get("views")
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _load_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _family_from_clip(clip: dict, text: str) -> str:
    explicit = str(clip.get("editorial_family") or clip.get("instagram_family") or "").strip().lower()
    if explicit:
        return explicit
    normalized = text.lower()
    if clip.get("preserve_composition") or clip.get("split_screen") or "split" in normalized:
        return "reaction_external_evidence"
    if "?" in text or re.search(r"\b(qual|como|por que|quem|quando|onde)\b", normalized):
        return "political_question_answer"
    if re.search(r"\b(pesquisa|gráfico|grafico|dados|números|numeros)\b", normalized):
        return "graph_evidence"
    if re.search(r"\b(evento|palco|debate|ato público|ato publico)\b", normalized):
        return "event_mobilization"
    # Antes isto devolvia "conversation_social", que por acaso é a família com a
    # maior mediana de views da tabela inteira — um milhão, vinda de um único
    # post. Ou seja: "não reconheci este trecho" virava o bônus máximo. Medido,
    # seis de dez textos caíam aqui, e entre eles uma receita de bolo e um
    # comentário de futebol, os dois pontuando acima de um trecho sobre
    # desestatização. Não reconhecer não é uma descoberta; devolve neutro, que é
    # o que o chamador já sabe tratar (available=False, sinal 50).
    return "desconhecida"


def _aggregate_records(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        family = str(record.get("family") or "unknown")[:80]
        groups.setdefault(family, []).append(record)

    family_priors = []
    layout_counts: dict[str, int] = {}
    for family, items in groups.items():
        views = [view for item in items if (view := _observed_view_count(item)) is not None]
        confidences = [max(0.0, min(1.0, _safe_float(item.get("confidence"), 0.5))) for item in items]
        preserve_count = sum(1 for item in items if str(item.get("layout_policy", "")).startswith("preserve"))
        for item in items:
            layout = str(item.get("layout") or "unknown")[:80]
            layout_counts[layout] = layout_counts.get(layout, 0) + 1
        family_priors.append({
            "family": family,
            "observations": len(items),
            "mean_views": round(mean(views), 1) if views else 0,
            "median_views": round(median(views), 1) if views else 0,
            "view_observation_count": len(views),
            "preserve_composition_rate": round(preserve_count / len(items), 3),
            "mean_annotation_confidence": round(mean(confidences), 3) if confidences else 0,
        })
    family_priors.sort(key=lambda item: (-item["observations"], -item["median_views"], item["family"]))
    return {
        "family_priors": family_priors,
        "layout_priors": [
            {"layout": layout, "observations": count}
            for layout, count in sorted(layout_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "record_count": sum(len(items) for items in groups.values()),
    }


@lru_cache(maxsize=4)
def load_editorial_priors(dataset_path: str = "") -> dict:
    """Load local detailed observations or aggregate packaged priors."""
    local_path = Path(dataset_path).expanduser() if dataset_path else LOCAL_DATASET_PATH
    local_payload = _load_json(local_path)
    if local_payload and isinstance(local_payload.get("records"), list):
        aggregate = _aggregate_records(local_payload["records"])
        return {
            **aggregate,
            "source": "local_detailed_dataset",
            "schema_version": local_payload.get("schema_version", "unknown"),
            "audio_status": (local_payload.get("annotation_contract") or {}).get("audio_status", "unknown"),
        }

    packaged = _load_json(PACKAGED_PRIORS_PATH) or {}
    aggregate = packaged.get("instagram_family_priors")
    if isinstance(aggregate, dict):
        return {**aggregate, "source": "packaged_aggregate_priors", "schema_version": packaged.get("schema_version", "unknown")}
    return {"family_priors": [], "layout_priors": [], "record_count": 0, "source": "none", "schema_version": "none"}


def build_editorial_pattern_prior(text: str, clip: dict | None = None, dataset_path: str = "") -> dict:
    """Return a bounded, explainable pattern prior for one candidate clip."""
    clip = clip if isinstance(clip, dict) else {}
    family = _family_from_clip(clip, str(text or ""))
    payload = load_editorial_priors(dataset_path)
    matches = [item for item in payload.get("family_priors", []) if item.get("family") == family]
    if not matches:
        return {
            "available": False,
            "family": family,
            "sample_count": 0,
            "signal": 50.0,
            "preserve_composition_rate": 0.0,
            "source": payload.get("source", "none"),
            "basis": "family_without_observations",
        }
    match = matches[0]
    all_views = [max(1.0, _safe_float(item.get("median_views"))) for item in payload.get("family_priors", []) if _safe_float(item.get("median_views")) > 0]
    baseline = median(all_views) if all_views else 1.0
    relative = math.log1p(max(1.0, _safe_float(match.get("median_views"))) / baseline)
    signal = max(42.0, min(58.0, 50.0 + (relative - 0.7) * 8.0))
    return {
        "available": True,
        "family": family,
        "sample_count": int(match.get("observations", 0) or 0),
        "signal": round(signal, 1),
        "preserve_composition_rate": round(_safe_float(match.get("preserve_composition_rate")), 3),
        "annotation_confidence": round(_safe_float(match.get("mean_annotation_confidence"), 0.5), 3),
        "source": payload.get("source", "unknown"),
        "basis": "observed_instagram_family_aggregate",
    }
