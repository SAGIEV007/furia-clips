"""Chub MCP enrichment bridge.

This module calls the Campaign Hub MCP directly only when the user has
opted in and a reachable endpoint is configured. It is deliberately
optional: every public method returns an empty payload on failure so
the rest of the app never blocks on MCP availability.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any


DEFAULT_URL = os.environ.get("CHUB_MCP_URL", "")
DEFAULT_TOKEN = os.environ.get("CHUB_MCP_TOKEN", "")
DEFAULT_ACCOUNT = os.environ.get("CHUB_MCP_ACCOUNT", "@renansantosmbl")


def _endpoint() -> str | None:
    return (DEFAULT_URL or "").strip() or None


def _headers() -> dict[str, str] | None:
    token = (DEFAULT_TOKEN or "").strip()
    if not token:
        return None
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
    }


def _post(payload: dict[str, Any]) -> dict[str, Any] | None:
    url = _endpoint()
    if not url:
        return None
    headers = _headers() or {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    try:
        import requests  # type: ignore
    except ImportError:
        return None
    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=30,
        )
        if response.status_code == 405:
            # Legacy SSE endpoint refusing POST. Do not treat as fatal.
            return None
        if response.status_code != 200:
            return None
        body = response.json()
        if isinstance(body, dict) and body.get("jsonrpc") == "2.0":
            return body.get("result")
        return body
    except Exception:
        return None


def _mcp(tool: str, arguments: dict[str, Any]) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) & 0xFFFF,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    result = _post(payload)
    if not isinstance(result, dict):
        return None
    content = result.get("content") or []
    texts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(item.get("text", ""))
    if not texts:
        return None
    try:
        return json.loads(texts[0])
    except (TypeError, ValueError):
        return texts[0]


def enrich_context_for_query(
    query: str,
    account: str = DEFAULT_ACCOUNT,
) -> dict[str, Any]:
    """Return lightweight Chub context for one editorial query."""
    if not query or not query.strip():
        return {}
    semantic = _mcp("chub_cohort_stats", {"query": query.strip(), "channel": account})
    if not isinstance(semantic, dict):
        return {}
    tag_hits = _mcp("chub_tag_performance", {"tag": query.strip(), "channel": account})
    if not isinstance(tag_hits, dict):
        tag_hits = {}
    return {
        "chub_semantic": semantic,
        "chub_tag_performance": tag_hits,
        "account": account,
    }


def enrich_campaign_priors(
    account: str = DEFAULT_ACCOUNT,
    limit: int = 5,
) -> dict[str, Any]:
    """Return top-performing organic creatives as editorial priors."""
    payload = _mcp(
        "chub_top_posts",
        {"metric": "ratio", "channel": account, "limit": int(limit)},
    )
    if not isinstance(payload, dict):
        return {}
    return {"chub_top_posts": payload, "account": account}


def enrich_audience_for_query(
    query: str,
    account: str = DEFAULT_ACCOUNT,
) -> dict[str, Any]:
    if not query or not query.strip():
        return {}
    payload = _mcp(
        "chub_audience",
        {"channel": account, "query": query.strip()},
    )
    if not isinstance(payload, dict):
        return {}
    return {"chub_audience": payload, "account": account}


def fetch_snapshot(
    account: str = DEFAULT_ACCOUNT,
) -> dict[str, Any] | None:
    """Build a Campaign Hub snapshot from live MCP tools.

    Returns a dict compatible with modules.campaign_hub.load_snapshot(),
    or None if the MCP is unreachable / misconfigured.
    """
    endpoint = _endpoint()
    if not endpoint:
        return None

    top_posts = _mcp(
        "chub_top_posts",
        {"metric": "ratio", "channel": account, "limit": 10},
    )
    if not isinstance(top_posts, dict):
        top_posts = {}

    transcript = _mcp(
        "chub_transcript",
        {"channel": account, "limit": 10},
    )
    if not isinstance(transcript, dict):
        transcript = {}

    stats = _mcp(
        "chub_acervo_stats",
        {"channel": account},
    )
    if not isinstance(stats, dict):
        stats = {}

    pauta = _mcp(
        "chub_acervo_pauta",
        {"channel": account, "limit": 20},
    )
    if not isinstance(pauta, dict):
        pauta = {}

    blocks = _mcp(
        "chub_acervo_blocks",
        {"channel": account, "limit": 20},
    )
    if not isinstance(blocks, dict):
        blocks = {}

    if not any([top_posts, transcript, stats, pauta, blocks]):
        return None

    return {
        "default_account": account,
        "accounts": {
            account: {
                "hook_observations": transcript.get("segments", [])[:20],
                "acervo_blocks": blocks.get("blocks", [])[:20],
                "acervo_pauta": pauta.get("pauta", [])[:20],
                "audience_priors": stats.get("audience", {}),
                "performance": top_posts,
            }
        },
        "meta": {
            "source": "chub_mcp_auto_snapshot",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        },
    }
