from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs" / "instagram-raw"
CATALOG = ROOT / "docs" / "instagram-full-catalog.csv"
SUMMARY = ROOT / "docs" / "instagram-full-summary.json"
LOG = ROOT / "docs" / "instagram-full-collection.log"
RAW.mkdir(parents=True, exist_ok=True)

PROFILES = {
    "renansantosreserva": {"id": "24031008826", "reported_posts": 330},
    "renansantosmbl": {"id": "2334727603", "reported_posts": 3497},
}
DELAY_SECONDS = 8.0
MAX_PAGES = 400
TIMEOUT_SECONDS = 45
MAX_429_RETRIES = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-IG-App-ID": "936619743392459",
    "X-ASBD-ID": "129477",
    "X-IG-WWW-Claim": "0",
    "X-Requested-With": "XMLHttpRequest",
}

session = requests.Session()
session.headers.update(HEADERS)

FIELDNAMES = [
    "profile",
    "feed_position",
    "page_number",
    "content_id",
    "shortcode",
    "content_type",
    "product_type",
    "taken_at_utc",
    "caption",
    "like_count",
    "comment_count",
    "video_view_count",
    "play_count",
    "width",
    "height",
    "display_url",
    "video_url",
    "url",
]


def log(message: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"arquivo inválido ignorado: {path.name}: {exc}")
        return None
    return value if isinstance(value, dict) else None


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def timeline_from_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    user = ((payload.get("data") or {}).get("user") or {})
    timeline = user.get("edge_owner_to_timeline_media") or {}
    edges = timeline.get("edges") or []
    nodes = [edge.get("node") or {} for edge in edges if isinstance(edge, dict)]
    page_info = timeline.get("page_info") or {}
    return nodes, page_info


def caption(node: dict[str, Any]) -> str:
    edges = ((node.get("edge_media_to_caption") or {}).get("edges") or [])
    if edges:
        return str(((edges[0].get("node") or {}).get("text") or "")).replace("\n", " ").strip()
    return ""


def iso_timestamp(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def node_row(profile: str, page_number: int, position: int, node: dict[str, Any]) -> dict[str, Any]:
    shortcode = str(node.get("shortcode") or "")
    is_video = bool(node.get("is_video"))
    product_type = str(node.get("product_type") or "")
    dimensions = node.get("dimensions") or {}
    display_url = str(node.get("display_url") or "")
    video_url = str(node.get("video_url") or "")
    path_kind = "reel" if is_video or product_type in {"clips", "igtv"} else "p"
    return {
        "profile": profile,
        "feed_position": position,
        "page_number": page_number,
        "content_id": str(node.get("id") or ""),
        "shortcode": shortcode,
        "content_type": "video" if is_video else "image_or_carousel",
        "product_type": product_type,
        "taken_at_utc": iso_timestamp(node.get("taken_at_timestamp")),
        "caption": caption(node),
        "like_count": (node.get("edge_media_preview_like") or {}).get("count", ""),
        "comment_count": (node.get("edge_media_to_comment") or {}).get("count", ""),
        "video_view_count": node.get("video_view_count", ""),
        "play_count": node.get("video_play_count", node.get("play_count", "")),
        "width": dimensions.get("width", ""),
        "height": dimensions.get("height", ""),
        "display_url": display_url,
        "video_url": video_url,
        "url": f"https://www.instagram.com/{path_kind}/{shortcode}/" if shortcode else "",
    }


def fetch_initial(profile: str) -> dict[str, Any]:
    existing = load_json(RAW / f"{profile}-profile.json")
    if existing:
        return existing
    response = session.get(
        "https://www.instagram.com/api/v1/users/web_profile_info/",
        params={"username": profile},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    save_json(RAW / f"{profile}-profile.json", payload)
    return payload


def fetch_page(profile: str, page_number: int, cursor: str) -> dict[str, Any]:
    path = RAW / f"{profile}-profile-page-{page_number:03d}.json"
    existing = load_json(path)
    if existing:
        time.sleep(DELAY_SECONDS)
        return existing
    params = {"username": profile, "max_id": cursor}
    for attempt in range(MAX_429_RETRIES + 1):
        response = session.get(
            "https://www.instagram.com/api/v1/users/web_profile_info/",
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code != 429:
            response.raise_for_status()
            payload = response.json()
            save_json(path, payload)
            time.sleep(DELAY_SECONDS)
            return payload
        retry_after = response.headers.get("Retry-After")
        try:
            server_wait = float(retry_after) if retry_after else 0.0
        except ValueError:
            server_wait = 0.0
        wait_seconds = max(server_wait, 60.0 * (attempt + 1))
        log(f"{profile}: HTTP 429 na página {page_number}; tentativa {attempt + 1}/{MAX_429_RETRIES + 1}, aguardando {wait_seconds:.0f}s")
        time.sleep(wait_seconds)
    raise RuntimeError(f"HTTP 429 persistente na página {page_number} após {MAX_429_RETRIES + 1} tentativas")


def read_existing_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not CATALOG.exists():
        return rows
    with CATALOG.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            key = f"{item.get('profile','')}:{item.get('shortcode','')}"
            if item.get("shortcode"):
                rows[key] = item
    return rows


def write_outputs(rows_by_key: dict[str, dict[str, Any]], summary: dict[str, Any]) -> None:
    rows = sorted(
        rows_by_key.values(),
        key=lambda row: (row.get("profile", ""), int(row.get("feed_position") or 0)),
    )
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_profile(profile: str, config: dict[str, Any], rows: dict[str, dict[str, Any]], summary: dict[str, Any]) -> None:
    initial = fetch_initial(profile)
    nodes, page_info = timeline_from_payload(initial)
    user = ((initial.get("data") or {}).get("user") or {})
    reported_count = ((user.get("edge_owner_to_timeline_media") or {}).get("count")) or config["reported_posts"]
    cursor = str(page_info.get("end_cursor") or "")
    has_next = bool(page_info.get("has_next_page"))
    profile_summary = summary.setdefault(profile, {
        "reported_posts": reported_count,
        "pages_completed": 0,
        "items_unique": 0,
        "video_items": 0,
        "image_or_carousel_items": 0,
        "errors": [],
        "page_status": [],
    })

    def absorb(page_number: int, page_nodes: list[dict[str, Any]]) -> tuple[int, int]:
        before = len(rows)
        for node_index, node in enumerate(page_nodes):
            shortcode = str(node.get("shortcode") or node.get("id") or "")
            if not shortcode:
                continue
            key = f"{profile}:{shortcode}"
            position = (page_number - 1) * 12 + node_index + 1
            rows[key] = node_row(profile, page_number, position, node)
        added = len(rows) - before
        videos = sum(1 for node in page_nodes if node.get("is_video"))
        return added, videos

    added, videos = absorb(1, nodes)
    profile_summary["pages_completed"] = max(profile_summary["pages_completed"], 1)
    profile_summary["items_unique"] = sum(1 for key in rows if key.startswith(profile + ":"))
    profile_summary["video_items"] = sum(1 for key, row in rows.items() if key.startswith(profile + ":") and row.get("content_type") == "video")
    profile_summary["image_or_carousel_items"] = profile_summary["items_unique"] - profile_summary["video_items"]
    if not any(item.get("page") == 1 for item in profile_summary["page_status"]):
        profile_summary["page_status"].append({"page": 1, "items": len(nodes), "new_items": added, "videos": videos, "has_next_page": has_next})

    log(f"{profile}: página 1/{MAX_PAGES}, itens={len(nodes)}, novos={added}, vídeos={videos}, mais={has_next}")
    write_outputs(rows, summary)

    page_number = 2
    seen_cursors = {cursor} if cursor else set()
    while has_next and cursor and page_number <= MAX_PAGES:
        try:
            payload = fetch_page(profile, page_number, cursor)
            nodes, page_info = timeline_from_payload(payload)
            next_cursor = str(page_info.get("end_cursor") or "")
            has_next = bool(page_info.get("has_next_page"))
            added, videos = absorb(page_number, nodes)
            profile_summary["pages_completed"] = max(profile_summary["pages_completed"], page_number)
            profile_summary["items_unique"] = sum(1 for key in rows if key.startswith(profile + ":"))
            profile_summary["video_items"] = sum(1 for key, row in rows.items() if key.startswith(profile + ":") and row.get("content_type") == "video")
            profile_summary["image_or_carousel_items"] = profile_summary["items_unique"] - profile_summary["video_items"]
            profile_summary["page_status"].append({"page": page_number, "items": len(nodes), "new_items": added, "videos": videos, "has_next_page": has_next})
            write_outputs(rows, summary)
            log(f"{profile}: página {page_number}/{MAX_PAGES}, itens={len(nodes)}, novos={added}, vídeos={videos}, mais={has_next}")
            if not next_cursor or next_cursor in seen_cursors:
                log(f"{profile}: cursor ausente ou repetido; encerrando com checkpoint preservado")
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
            page_number += 1
        except Exception as exc:
            error = {"page": page_number, "error": repr(exc)}
            profile_summary["errors"].append(error)
            write_outputs(rows, summary)
            log(f"{profile}: erro na página {page_number}: {exc!r}")
            break

    if page_number > MAX_PAGES and has_next:
        log(f"{profile}: limite de {MAX_PAGES} páginas atingido; checkpoint preservado")


def main() -> int:
    if LOG.exists():
        LOG.unlink()
    rows = read_existing_rows()
    summary: dict[str, Any] = {}
    for profile, config in PROFILES.items():
        collect_profile(profile, config, rows, summary)
    write_outputs(rows, summary)
    log("coleta concluída ou interrompida com checkpoint disponível")
    return 0


if __name__ == "__main__":
    sys.exit(main())
