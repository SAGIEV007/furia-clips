from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs" / "instagram-raw"
CATALOG = ROOT / "docs" / "instagram-full-catalog.csv"
SUMMARY = ROOT / "docs" / "instagram-full-summary.json"
RAW.mkdir(parents=True, exist_ok=True)

PROFILES = {
    "renansantosreserva": "24031008826",
    "renansantosmbl": "2334727603",
}
COUNT = 12
DELAY_SECONDS = 1.5
MAX_PAGES = 400
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    "x-ig-app-id": "936619743392459",
    "x-requested-with": "XMLHttpRequest",
    "Accept": "application/json",
}

session = requests.Session()
session.headers.update(HEADERS)
summary = {}
rows = []


def page_payload(username: str, number: int):
    path = RAW / f"{username}-feed-page-{number:03d}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")), path
        except json.JSONDecodeError:
            path.unlink()
    return None, path


def fetch_page(username: str, user_id: str, number: int, max_id: str | None):
    payload, path = page_payload(username, number)
    if payload is not None:
        return payload
    params = {"count": COUNT}
    if max_id:
        params["max_id"] = max_id
    response = session.get(f"https://www.instagram.com/api/v1/feed/user/{user_id}/", params=params, timeout=45)
    response.raise_for_status()
    payload = response.json()
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    time.sleep(DELAY_SECONDS)
    return payload


def caption_text(item: dict) -> str:
    caption = item.get("caption") or {}
    if isinstance(caption, dict):
        return str(caption.get("text") or "").replace("\n", " ").strip()
    return ""


def item_row(username: str, position: int, item: dict) -> dict:
    is_video = bool(item.get("media_type") == 2 or item.get("video_versions") or item.get("is_unified_video"))
    product_type = str(item.get("product_type") or "")
    code = str(item.get("code") or item.get("shortcode") or "")
    path_kind = "reel" if is_video or product_type in {"clips", "igtv"} else "p"
    taken_at = item.get("taken_at")
    taken_at_utc = ""
    if taken_at:
        taken_at_utc = datetime.fromtimestamp(int(taken_at), tz=timezone.utc).isoformat()
    return {
        "profile": username,
        "position_in_consolidated_feed": position,
        "content_id": str(item.get("pk") or item.get("id") or ""),
        "code": code,
        "content_type": "video" if is_video else "image_or_carousel",
        "product_type": product_type,
        "taken_at_utc": taken_at_utc,
        "caption": caption_text(item),
        "like_count": item.get("like_count", ""),
        "comment_count": item.get("comment_count", ""),
        "view_count": item.get("view_count", item.get("play_count", "")),
        "play_count": item.get("play_count", ""),
        "width": item.get("original_width", ""),
        "height": item.get("original_height", ""),
        "url": f"https://www.instagram.com/{path_kind}/{code}/" if code else "",
    }

for username, user_id in PROFILES.items():
    all_items = []
    seen_codes = set()
    page_number = 1
    max_id = None
    page_status = []

    while page_number <= MAX_PAGES:
        try:
            payload = fetch_page(username, user_id, page_number, max_id)
        except Exception as exc:
            page_status.append({"page": page_number, "error": str(exc)})
            break
        items = payload.get("items") or []
        unique_items = []
        for item in items:
            code = str(item.get("code") or item.get("shortcode") or item.get("pk") or item.get("id") or "")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_items.append(item)
                all_items.append(item)
        next_max_id = payload.get("next_max_id")
        more_available = bool(payload.get("more_available"))
        page_status.append({
            "page": page_number,
            "items_returned": len(items),
            "new_items": len(unique_items),
            "next_max_id_present": bool(next_max_id),
            "more_available": more_available,
        })
        print(f"{username}: pagina {page_number}, {len(unique_items)} novos, mais={more_available}")
        if not more_available or not next_max_id or next_max_id == max_id:
            break
        max_id = next_max_id
        page_number += 1

    for position, item in enumerate(all_items, start=1):
        rows.append(item_row(username, position, item))
    summary[username] = {
        "pages_attempted": len(page_status),
        "items_unique": len(all_items),
        "video_items": sum(1 for item in all_items if item.get("media_type") == 2 or item.get("video_versions") or item.get("is_unified_video")),
        "items_with_view_count": sum(1 for item in all_items if item.get("view_count") or item.get("play_count")),
        "page_status": page_status,
    }

fields = list(rows[0].keys()) if rows else ["profile", "code", "url"]
with CATALOG.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
