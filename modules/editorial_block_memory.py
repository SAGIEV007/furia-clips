"""Read-only block retrieval from the local Campaign Hub memory."""

from __future__ import annotations

from typing import Any

from .campaign_hub_memory import read_memory


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _matches(block: dict[str, Any], query: str, video_id: str | None, renan_speaking: bool | None) -> bool:
    if video_id and str(block.get("video_id") or "") != str(video_id):
        return False
    if renan_speaking is not None and bool(block.get("renan_speaking")) is not renan_speaking:
        return False
    if query:
        haystack = " ".join(
            str(block.get(key) or "")
            for key in ("title", "summary", "trigger_question", "category", "video_id")
        ).lower()
        haystack += " " + " ".join(str(item) for item in (block.get("topics") or []))
        if query.lower().strip() not in haystack:
            return False
    return True


def _source_index(memory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in (memory.get("records") or {}).get("sources", [])
        if isinstance(item, dict) and item.get("id")
    }


def _present(block: dict[str, Any], source: dict[str, Any], highlights: list[dict[str, Any]]) -> dict[str, Any]:
    start = _as_float(block.get("start_s"))
    end = _as_float(block.get("end_s"), start)
    return {
        "id": block.get("id"),
        "title": block.get("title") or "bloco editorial",
        "summary": block.get("summary") or "",
        "category": block.get("category") or "",
        "topics": block.get("topics") or [],
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(max(0.0, end - start), 3),
        "video_id": block.get("video_id") or "",
        "source": source,
        "trigger_question": block.get("trigger_question") or "",
        "renan_speaking": block.get("renan_speaking"),
        "self_contained_rank": block.get("self_contained_rank"),
        "density_rank": block.get("density_rank"),
        "needs_context": bool(block.get("needs_context")),
        "possible_cuts": block.get("possible_cuts"),
        "risk_flags": block.get("risk_flags") or [],
        "gate_warnings": block.get("gate_warnings") or [],
        "trust_tier": block.get("trust_tier") or "",
        "highlight_count": len(highlights),
        "highlights": highlights,
        "download_mode": "local_interval_when_source_available",
    }


def list_blocks(
    path: str | None = None,
    *,
    query: str = "",
    video_id: str | None = None,
    renan_speaking: bool | None = None,
    prioritize_renan: bool = False,
    source_ref: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    memory = read_memory(path)
    if not memory:
        return {"available": False, "blocks": [], "total": 0, "message": "Memória local indisponível."}
    blocks = (memory.get("records") or {}).get("blocks", [])
    highlights_by_block: dict[str, list[dict[str, Any]]] = {}
    for highlight in (memory.get("records") or {}).get("highlights", []):
        if isinstance(highlight, dict):
            highlights_by_block.setdefault(str(highlight.get("block_id") or ""), []).append(highlight)
    source_index = _source_index(memory)
    source_ref = str(source_ref or "").strip()
    filtered = []
    for block in blocks:
        if not isinstance(block, dict) or not _matches(block, query, video_id, renan_speaking):
            continue
        if source_ref:
            source = source_index.get(str(block.get("video_id") or ""), {})
            known_refs = {str(source.get("id") or ""), str(source.get("youtube_id") or ""), str(source.get("url") or "")}
            if source_ref not in known_refs:
                continue
        filtered.append(block)
    if prioritize_renan:
        filtered.sort(key=lambda item: (0 if item.get("renan_speaking") is True else 1, _as_float(item.get("start_s")), str(item.get("id") or "")))
    else:
        filtered.sort(key=lambda item: (_as_float(item.get("start_s")), str(item.get("id") or "")))
    safe_limit = max(1, min(500, int(limit or 50)))
    safe_offset = max(0, int(offset or 0))
    page = filtered[safe_offset:safe_offset + safe_limit]
    return {
        "available": True,
        "status": "ready",
        "memory_version": memory.get("version", ""),
        "total": len(filtered),
        "offset": safe_offset,
        "limit": safe_limit,
        "blocks": [
            _present(block, source_index.get(str(block.get("video_id") or ""), {}), highlights_by_block.get(str(block.get("id") or ""), []))
            for block in page
        ],
    }


def get_block(block_id: str, path: str | None = None) -> dict[str, Any] | None:
    result = list_blocks(path, limit=500)
    for block in result.get("blocks", []):
        if str(block.get("id")) == str(block_id):
            sentences = [
                item for item in (read_memory(path) or {}).get("records", {}).get("sentences", [])
                if isinstance(item, dict) and str(item.get("block_id")) == str(block_id)
            ]
            block["sentences"] = sentences[:2000]
            return block
    return None
