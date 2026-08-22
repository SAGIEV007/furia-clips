"""Busca editorial local sobre evidências exportadas do Campaign Hub.

O Furia não acessa o conector diretamente no notebook. Esta camada lê apenas
snapshots JSON previamente exportados por uma consulta somente leitura e deixa
explícitos os limites: links podem existir sem timestamps ou sem download
autorizado. Nenhuma função deste módulo escreve no Campaign Hub.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CACHE_DIR = Path(
    os.environ.get("FURIA_CLIPS_CHUB_CACHE_DIR", "")
    or Path.home() / "FuriaClipsData" / "analyses" / "campaign_hub_queries"
)
DEFAULT_PROFILE_PATH = Path(
    os.environ.get("FURIA_CAMPAIGN_HUB_SNAPSHOT", "")
    or Path.home() / "FuriaClipsData" / "campaign_hub" / "profile.json"
)
_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
    "e", "ou", "em", "no", "na", "nos", "nas", "para", "por", "com",
    "que", "sobre", "falando", "falar", "fala", "video", "videos", "conteudo",
}


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _tokens(value: Any) -> set[str]:
    return {
        token for token in re.findall(r"[\w-]+", _normalize(value))
        if len(token) > 2 and token not in _STOPWORDS
    }


def _decode_result_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        for item in payload["content"]:
            text = item.get("text") if isinstance(item, dict) else None
            if isinstance(text, str):
                try:
                    decoded = json.loads(text)
                    if isinstance(decoded, dict):
                        return decoded
                except ValueError:
                    continue
    return payload if isinstance(payload, dict) else None


def _snapshot_rows(decoded: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract row lists from the known local export envelopes."""
    for key in ("results", "rows", "items", "mentions", "data"):
        value = decoded.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            for nested_key in ("results", "rows", "items", "mentions"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return [row for row in nested if isinstance(row, dict)]
    return []


def _iter_cached_records(cache_dir: Path) -> Iterable[dict[str, Any]]:
    if not cache_dir.exists():
        return
    for path in sorted(cache_dir.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        decoded = _decode_result_file(path)
        if not decoded:
            continue
        envelope_account = str(decoded.get("channel") or decoded.get("account") or "").strip()
        envelope_platform = str(decoded.get("platform") or "").strip().lower()
        for row in _snapshot_rows(decoded):
            record = dict(row)
            if envelope_account and not str(record.get("channel") or record.get("account") or "").strip():
                record["channel"] = envelope_account
            if envelope_account and not str(record.get("account") or "").strip():
                record["account"] = envelope_account
            if envelope_platform and not str(record.get("platform") or "").strip():
                record["platform"] = envelope_platform
            record["_cache_file"] = str(path)
            record["_query_mode"] = decoded.get("mode", "cached")
            record["_total_mentions"] = decoded.get("totalMentions")
            yield record


def _iter_profile_records(profile_path: Path | None = None) -> Iterable[dict[str, Any]]:
    """Read rich blocks/pauta from the persistent snapshot without writing to it."""
    path = profile_path or DEFAULT_PROFILE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("accounts"), dict):
        return
    for account, account_data in payload["accounts"].items():
        if not isinstance(account_data, dict):
            continue
        for key, mode in (("acervo_blocks", "acervo_block"), ("blocks", "acervo_block"), ("acervo_pauta", "acervo_pauta"), ("pauta_candidates", "acervo_pauta")):
            rows = account_data.get(key, [])
            if isinstance(rows, dict):
                rows = rows.get("items", rows.get("results", []))
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                record = dict(row)
                record["channel"] = str(account)
                record["account"] = str(account)
                record["_cache_file"] = str(path)
                record["_query_mode"] = mode
                record["_profile_snapshot"] = True
                yield record


def _parse_date_filter(value: Any, field_name: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"{field_name} precisa estar no formato AAAA-MM-DD.") from exc


def _published_date(record: dict[str, Any]) -> date | None:
    value = record.get("publishedAt") or record.get("published_at") or record.get("publishedDate")
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _parse_timestamp(value: Any) -> float | None:
    """Parse seconds or a real HH:MM:SS/MM:SS timecode, never arbitrary text."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if numeric >= 0 else None
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
        return numeric if numeric >= 0 else None
    except ValueError:
        pass
    match = re.fullmatch(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,](\d+))?", text)
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    hours_value = int(hours or 0)
    minutes_value = int(minutes)
    seconds_value = int(seconds)
    if minutes_value >= 60 or seconds_value >= 60:
        return None
    total = hours_value * 3600 + minutes_value * 60 + seconds_value
    if fraction:
        total += float(f"0.{fraction}")
    return total


def _has_timestamps(record: dict[str, Any]) -> bool:
    """Return true only when the cached record contains usable timing evidence."""
    for key in ("start", "startTime", "timestamp", "timecode", "startS", "start_seconds", "startTimeS"):
        if _parse_timestamp(record.get(key)) is not None:
            return True
    if any(_parse_timestamp(record.get(key)) is not None for key in ("end", "endTime", "endS", "end_seconds", "endTimeS")):
        return _parse_timestamp(record.get("start")) is not None or _parse_timestamp(record.get("startS")) is not None or _parse_timestamp(record.get("start_seconds")) is not None
    segments = record.get("segments") or record.get("transcriptSegments") or record.get("sentences")
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = _parse_timestamp(segment.get("start", segment.get("startTime", segment.get("startS"))))
        end = _parse_timestamp(segment.get("end", segment.get("endTime", segment.get("endS"))))
        if start is not None and end is not None and end > start:
            return True
    return False


def _performance_signal(record: dict[str, Any]) -> float:
    for key in ("settledRatio", "ratio", "performanceRatio"):
        try:
            value = float(record.get(key))
            if value >= 0:
                return value
        except (TypeError, ValueError):
            continue
    return 0.0


def _source_video(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("video") or record.get("sourceVideo") or record.get("source_video")
    return value if isinstance(value, dict) else {}


def _first_value(record: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return default


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _list_labels(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;|]", value) if part.strip()]
    if not isinstance(value, list):
        return []
    labels = []
    for item in value:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
        elif isinstance(item, dict):
            label = _first_value(item, "label", "name", "title", "topic", "text")
            if str(label).strip():
                labels.append(str(label).strip())
    return labels


def _remote_preview_url(source_url: str, source_video_id: Any, start_seconds: float | None = None) -> str:
    """Build a canonical, timestamped preview link without downloading media."""
    raw_url = str(source_url or "").strip()
    if not re.match(r"^https?://", raw_url, re.IGNORECASE):
        return ""
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return ""
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}:
        return ""
    video_id = str(source_video_id or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        path = "/watch"
        query = {"v": [video_id]}
    else:
        path = parsed.path or "/watch"
        query = parse_qs(parsed.query, keep_blank_values=False)
        if host.endswith("youtu.be") and path.strip("/"):
            query = {"v": [path.strip("/")]}
            path = "/watch"
    query.pop("si", None)
    if start_seconds is not None and start_seconds >= 0:
        query["t"] = [str(max(0, int(round(start_seconds)))) + "s"]
    return urlunsplit(("https", "www.youtube.com", path, urlencode(query, doseq=True), ""))


def _normalise_moments(record: dict[str, Any], *, source_url: str = "", source_video_id: Any = "") -> list[dict[str, Any]]:
    raw = _first_value(record, "moments", "highlights", "blockHighlights", "strongMoments", default=[])
    if not isinstance(raw, list):
        return []
    moments = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            moments.append({"label": item.strip(), "reason": "", "start_seconds": None, "end_seconds": None})
            continue
        if not isinstance(item, dict):
            continue
        start = _coerce_number(_first_value(item, "startS", "start_seconds", "start", "timestamp", default=None))
        end = _coerce_number(_first_value(item, "endS", "end_seconds", "end", default=None))
        moment = {
            "label": str(_first_value(item, "label", "title", "name", "kind", default="Momento forte")).strip(),
            "reason": str(_first_value(item, "reason", "rationale", "description", "text", default="")).strip(),
            "start_seconds": start,
            "end_seconds": end,
            "score": _coerce_number(_first_value(item, "score", "strength", default=None)),
        }
        preview_url = _remote_preview_url(source_url, source_video_id, start)
        if preview_url:
            moment["preview_url"] = preview_url
        moments.append(moment)
    return moments


def _search_text(record: dict[str, Any]) -> str:
    """Return the best locally available textual evidence for a cached record."""
    for key in ("fullScript", "full_script", "transcript", "transcriptText", "text", "caption"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    segments = record.get("segments") or record.get("transcriptSegments") or record.get("sentences")
    if isinstance(segments, list):
        joined = " ".join(
            str(segment.get("text", "")).strip()
            for segment in segments
            if isinstance(segment, dict) and str(segment.get("text", "")).strip()
        ).strip()
        if joined:
            return joined
    fallback_parts = [
        _first_value(record, "title", "blockTitle", "label", "name"),
        _first_value(record, "summary", "description", "abstract"),
        _first_value(record, "triggerQuestion", "trigger_question"),
        " ".join(_list_labels(_first_value(record, "topics", "tags", default=[]))),
    ]
    return " ".join(str(part).strip() for part in fallback_parts if str(part).strip()).strip()


def _semantic_signal(record: dict[str, Any]) -> float:
    for key in ("similarity", "semanticScore", "semantic_score", "fusionScore", "fusion_score"):
        value = _coerce_number(record.get(key))
        if value is not None:
            return max(0.0, min(1.0, value))
    return 0.0


def _block_dossier(record: dict[str, Any], *, source_url: str, source_platform: str) -> dict[str, Any]:
    video = _source_video(record)
    start = _coerce_number(_first_value(record, "startS", "start_seconds", "startTime", "start", "timestamp", default=None))
    end = _coerce_number(_first_value(record, "endS", "end_seconds", "endTime", "end", default=None))
    duration = _coerce_number(_first_value(record, "durationS", "duration_seconds", "duration", "lengthS", default=None))
    if duration is None and start is not None and end is not None and end > start:
        duration = end - start
    source_video_id = _first_value(video, "id", "youtubeId", "videoId", default=_first_value(record, "videoId", "video_id", default=""))
    moments = _normalise_moments(record, source_url=source_url, source_video_id=source_video_id)
    preview_url = _remote_preview_url(source_url, source_video_id, start)
    return {
        "block_id": _first_value(record, "id", "blockId", "block_id"),
        "block_version_id": _first_value(record, "blockVersionId", "block_version_id"),
        "sentence_table_id": _first_value(record, "sentenceTableId", "sentence_table_id"),
        "source_ref": _first_value(record, "sourceRef", "source_ref"),
        "chunk_index": _first_value(record, "chunkIndex", "chunk_index", default=None),
        "title": str(_first_value(record, "title", "blockTitle", "label", "name", default="")).strip(),
        "summary": str(_first_value(record, "summary", "description", "abstract", default="")).strip(),
        "category": str(_first_value(record, "category", "categoryLabel", default="")).strip(),
        "topics": _list_labels(_first_value(record, "topics", "tags", default=[])),
        "trigger_question": str(_first_value(record, "triggerQuestion", "trigger_question", default="")).strip(),
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": duration,
        "possible_cuts": _first_value(record, "possibleCuts", "possible_cuts", default=None),
        "density_rank": _first_value(record, "densityRank", "density_rank", default=None),
        "self_contained_rank": _first_value(record, "selfContainedRank", "self_contained_rank", default=None),
        "needs_context": bool(_first_value(record, "needsContext", "needs_context", default=False)),
        "renan_speaking": _first_value(record, "renanSpeaking", "renan_speaking", default=None),
        "risk_flags": _list_labels(_first_value(record, "riskFlags", "risk_flags", default=[])),
        "gate_warnings": _list_labels(_first_value(record, "gateWarnings", "gate_warnings", default=[])),
        "trust_tier": str(_first_value(record, "trustTier", "trust_tier", default="")).strip(),
        "trust_tier_label": str(_first_value(record, "trustTierLabel", "trust_tier_label", default="")).strip(),
        "moments": moments,
        "primary_reason": str(_first_value(record, "selfContainedReason", "primaryReason", "reason", "rationale", default="")).strip(),
        "caption_provenance_note": str(_first_value(record, "captionProvenanceNote", "caption_provenance_note", default="")).strip(),
        "source_title": str(_first_value(video, "title", "name", default=_first_value(record, "sourceTitle", "source_title", default=""))).strip(),
        "source_url": str(source_url).strip(),
        "source_video_id": source_video_id,
        "source_platform": str(_first_value(video, "platform", default=source_platform)).strip().lower(),
        "source_preview_url": preview_url,
        "source_preview_kind": "youtube_timestamped" if preview_url and start is not None else "youtube_source" if preview_url else "unavailable",
        "source_preview_available": bool(preview_url),
        "source_channel": str(_first_value(video, "youtubeChannelId", "channel", default="")).strip(),
        "source_published_at": _first_value(video, "publishedAt", "published_at", default=""),
        "source_duration_seconds": _coerce_number(_first_value(video, "durationS", "duration_seconds", "duration", default=None)),
        "transcript_source": str(_first_value(record, "transcriptSource", "transcript_source", default="")).strip(),
    }


def _editorial_score(record: dict[str, Any], query_tokens: set[str], max_ratio: float) -> tuple[float, float, float]:
    script = _search_text(record)
    lexical_tokens = _tokens(script)
    lexical = len(query_tokens & lexical_tokens) / max(1, len(query_tokens))
    semantic = _semantic_signal(record)
    ratio = _performance_signal(record)
    normalized_ratio = ratio / max_ratio if max_ratio > 0 else 0.0
    # Relevância domina; performance é um sinal limitado e account-local.
    score = (semantic * 70.0) + (lexical * 20.0) + (normalized_ratio * 10.0)
    return round(score, 2), round(semantic, 4), round(lexical, 4)


def search_cached_campaign_hub(
    query: str,
    *,
    account: str | None = None,
    platform: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
    limit: int = 25,
    cache_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Search only local, read-only Campaign Hub exports.

    Results are ranked separately within each account baseline before being
    merged. The response deliberately exposes whether timestamps/download are
    actually available instead of implying that every link is downloadable.
    """
    query = str(query or "").strip()
    if not query:
        raise ValueError("Informe um assunto para pesquisar.")
    limit = max(1, min(50, int(limit or 25)))
    selected_account = str(account or "").strip() or None
    selected_platform = str(platform or "").strip().lower() or None
    start_date = _parse_date_filter(published_from, "published_from")
    end_date = _parse_date_filter(published_to, "published_to")
    if start_date and end_date and start_date > end_date:
        raise ValueError("published_from não pode ser posterior a published_to.")
    query_tokens = _tokens(query)
    if not query_tokens:
        raise ValueError("A consulta precisa ter palavras suficientes para pesquisa.")
    root = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    candidates = []
    for record in _iter_cached_records(root):
        row_account = str(record.get("channel") or record.get("account") or "").strip()
        video = _source_video(record)
        row_platform = str(_first_value(video, "platform", default=record.get("platform") or "")).strip().lower()
        if selected_account and row_account != selected_account:
            continue
        if selected_platform and row_platform != selected_platform:
            continue
        if start_date or end_date:
            published = _published_date(record)
            if published is None:
                continue
            if start_date and published < start_date:
                continue
            if end_date and published > end_date:
                continue
        candidates.append(record)
    # A rich profile snapshot is a separate source from query result caches. It
    # is included only when it exists and is still filtered by account/platform/date.
    for record in _iter_profile_records():
        row_account = str(record.get("channel") or record.get("account") or "").strip()
        video = _source_video(record)
        row_platform = str(_first_value(video, "platform", default=record.get("platform") or "youtube")).strip().lower()
        if selected_account and row_account != selected_account:
            continue
        if selected_platform and row_platform != selected_platform:
            continue
        if start_date or end_date:
            published = _published_date(record)
            if published is None:
                continue
            if start_date and published < start_date:
                continue
            if end_date and published > end_date:
                continue
        candidates.append(record)
    account_max_ratio: dict[str, float] = {}
    for record in candidates:
        account_key = str(record.get("channel") or record.get("account") or "unknown")
        account_max_ratio[account_key] = max(account_max_ratio.get(account_key, 0.0), _performance_signal(record))
    ranked = []
    seen_account_urls: set[tuple[str, str]] = set()
    for record in candidates:
        video = _source_video(record)
        record_url = str(_first_value(record, "url", "sourceUrl", "source_url", "youtubeUrl", default="")).strip()
        nested_url = str(_first_value(video, "url", "sourceUrl", "youtubeUrl", default="")).strip()
        nested_platform = str(_first_value(video, "platform", default=record.get("platform") or "")).strip().lower()
        url = nested_url if nested_platform == "youtube" and nested_url else record_url or nested_url
        account_key = str(record.get("channel") or record.get("account") or "unknown")
        dedupe_key = (account_key, url)
        if not url or dedupe_key in seen_account_urls:
            continue
        score, semantic, lexical = _editorial_score(record, query_tokens, account_max_ratio.get(account_key, 0.0))
        if score <= 0:
            continue
        seen_account_urls.add(dedupe_key)
        dossier = _block_dossier(record, source_url=url, source_platform=str(record.get("platform") or "unknown"))
        has_timestamps = _has_timestamps(record) or (
            dossier["start_seconds"] is not None and dossier["end_seconds"] is not None and dossier["end_seconds"] > dossier["start_seconds"]
        )
        published_at = record.get("publishedAt") or record.get("published_at") or record.get("publishedDate") or dossier["source_published_at"]
        row = {
            "url": url,
            "channel": account_key,
            "platform": str(record.get("platform") or dossier["source_platform"] or "unknown"),
            "published_at": published_at,
            "full_script": _search_text(record),
            "caption": record.get("caption") or video.get("caption") or "",
            "hook_family": record.get("hook") or record.get("hookFamily") or "",
            "tags": _list_labels(_first_value(record, "tags", "topics", default=[])),
            "similarity": semantic,
            "semantic_score": semantic,
            "lexical_match": lexical,
            "lexical_score": _coerce_number(record.get("lexicalScore")),
            "fusion_score": _coerce_number(record.get("fusionScore")),
            "producing_mode": str(record.get("producingMode") or "").strip(),
            "performance_ratio": _performance_signal(record),
            "editorial_score": score,
            "has_timestamps": has_timestamps,
            "download_status": "timestamps_available" if has_timestamps else "link_only_no_timestamps",
            "download_eligible": bool(has_timestamps and re.match(r"^https?://", url)),
            "download_action_available": False,
            "source": "campaign_hub_local_snapshot",
            "read_only": True,
        }
        row.update(dossier)
        ranked.append(row)
    ranked.sort(key=lambda item: (-item["editorial_score"], item["channel"], item["url"]))
    account_counts: dict[str, int] = {}
    for item in ranked:
        account_counts[item["channel"]] = account_counts.get(item["channel"], 0) + 1
    return {
        "success": True,
        "query": query,
        "account": selected_account,
        "platform": selected_platform,
        "published_from": start_date.isoformat() if start_date else None,
        "published_to": end_date.isoformat() if end_date else None,
        "source": "campaign_hub_local_snapshot",
        "read_only": True,
        "cache_dir": str(root),
        "total_cached_matches": len(ranked),
        "returned": min(limit, len(ranked)),
        "counts": {
            "accounts": account_counts,
            "with_timestamps": sum(1 for item in ranked if item["has_timestamps"]),
            "download_eligible": sum(1 for item in ranked if item["download_eligible"]),
        },
        "limits": [
            "O snapshot local pode estar desatualizado.",
            "Caption e transcrição são evidência de busca, não prova factual.",
            "URL e timestamps não significam que o download esteja disponível neste cliente local; a ação precisa de uma fonte autorizada.",
        ],
        "results": ranked[:limit],
    }
