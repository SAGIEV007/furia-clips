"""Métricas observadas para calibração editorial, sem confundir alcance com qualidade.

O módulo usa somente dados fornecidos pelo usuário, por exportação autorizada ou por
integrações futuras. Ele não tenta inferir a fórmula privada de XP/ranking de terceiros.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import log1p
from typing import Any

SUPPORTED_PLATFORMS = {"instagram", "youtube", "tiktok", "other"}
SUPPORTED_FORMATS = {"vertical_916", "square_alfinetei", "fake_tweet", "unknown"}
SUPPORTED_WINDOWS = {"today", "week", "month", "all"}
SUPPORTED_REGIONS = {"brasil", "state", "city", "all"}


def _number(value: Any, *, integer: bool = False, minimum: float = 0) -> int | float:
    if value in (None, ""):
        return 0 if integer else 0.0
    try:
        parsed = int(float(value)) if integer else float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("métrica numérica inválida") from exc
    if parsed < minimum:
        raise ValueError("métrica não pode ser negativa")
    return parsed


def _timestamp(value: Any, *, default_now: bool = False) -> str | None:
    if value in (None, ""):
        return datetime.now(timezone.utc).isoformat() if default_now else None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("timestamp inválido; use ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _age_hours(published_at: str | None, collected_at: str | None) -> float | None:
    if not published_at or not collected_at:
        return None
    published = datetime.fromisoformat(published_at)
    collected = datetime.fromisoformat(collected_at)
    seconds = max(0.0, (collected - published).total_seconds())
    return round(seconds / 3600, 3)


def normalize_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one authorized performance observation."""
    if not isinstance(payload, dict):
        raise ValueError("snapshot deve ser um objeto")
    content_key = str(payload.get("content_key", "") or "").strip()[:180]
    if not content_key:
        raise ValueError("content_key é obrigatório")
    platform = str(payload.get("platform", "other") or "other").strip().lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError("plataforma inválida")
    format_id = str(payload.get("format_id", "unknown") or "unknown").strip()
    if format_id not in SUPPORTED_FORMATS:
        format_id = "unknown"
    account_key = str(payload.get("account_key", "") or "").strip()[:180]
    observation_window = str(payload.get("observation_window", "all") or "all").strip().lower()
    if observation_window not in SUPPORTED_WINDOWS:
        observation_window = "all"
    region = str(payload.get("region", "all") or "all").strip().lower()[:40]
    if region not in SUPPORTED_REGIONS:
        region = "all"
    collected_at = _timestamp(payload.get("collected_at"), default_now=True)
    published_at = _timestamp(payload.get("published_at"))
    views = _number(payload.get("views"), integer=True)
    likes = _number(payload.get("likes"), integer=True)
    comments = _number(payload.get("comments"), integer=True)
    shares = _number(payload.get("shares"), integer=True)
    saves = _number(payload.get("saves"), integer=True)
    engagement_actions = likes + comments + shares + saves
    engagement_rate = round(engagement_actions / views, 6) if views else None
    age_hours = _age_hours(published_at, collected_at)
    velocity = round(views / max(age_hours, 1.0), 3) if age_hours is not None else None
    return {
        "content_key": content_key,
        "platform": platform,
        "format_id": format_id,
        "account_key": account_key,
        "observation_window": observation_window,
        "region": region,
        "published_at": published_at,
        "collected_at": collected_at,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_actions": engagement_actions,
        "engagement_rate": engagement_rate,
        "age_hours": age_hours,
        "view_velocity_per_hour": velocity,
        "ranking_position": _number(payload.get("ranking_position"), integer=True) or None,
        "xp": _number(payload.get("xp"), integer=False) or None,
        "collection_state": str(payload.get("collection_state", "observed") or "observed")[:40],
        "source": str(payload.get("source", "manual_or_authorized_export") or "manual_or_authorized_export")[:80],
    }


def compare_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare two normalized observations of the same content."""
    previous_views = int(previous.get("views") or 0)
    current_views = int(current.get("views") or 0)
    delta = current_views - previous_views
    growth = round(delta / previous_views, 6) if previous_views else None
    return {
        "views_delta": delta,
        "views_growth_rate": growth,
        "collection_interval_hours": _age_hours(
            previous.get("collected_at"), current.get("collected_at")
        ),
    }


def cohort_observed_score(snapshot: dict[str, Any], cohort: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank an item only against a supplied real cohort; never fabricate a baseline."""
    valid = [item for item in cohort if isinstance(item, dict)]
    if not valid:
        return {"score": None, "basis": "no_cohort"}

    def percentile(key: str) -> float | None:
        values = [float(item[key]) for item in valid if item.get(key) is not None]
        value = snapshot.get(key)
        if value is None or not values:
            return None
        return round(100.0 * sum(candidate <= float(value) for candidate in values) / len(values), 2)

    views_pct = percentile("views")
    engagement_pct = percentile("engagement_rate")
    velocity_pct = percentile("view_velocity_per_hour")
    available = [(views_pct, 0.5), (engagement_pct, 0.3), (velocity_pct, 0.2)]
    available = [(value, weight) for value, weight in available if value is not None]
    score = round(sum(value * weight for value, weight in available) / sum(weight for _, weight in available), 2) if available else None
    return {
        "score": score,
        "basis": "supplied_cohort" if score is not None else "insufficient_metrics",
        "components": {
            "views_percentile": views_pct,
            "engagement_percentile": engagement_pct,
            "velocity_percentile": velocity_pct,
        },
    }


def metric_labels(snapshot: dict[str, Any]) -> list[str]:
    """Return explanatory labels for UI cards, not a viral guarantee."""
    labels = []
    if snapshot.get("view_velocity_per_hour") is not None:
        labels.append("velocidade observada")
    if snapshot.get("engagement_rate") is not None:
        labels.append("engajamento observado")
    if snapshot.get("ranking_position") is not None:
        labels.append("posição informada")
    if snapshot.get("collection_state"):
        labels.append(f"coleta: {snapshot['collection_state']}")
    return labels
