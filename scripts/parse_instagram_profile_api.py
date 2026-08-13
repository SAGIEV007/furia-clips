from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs" / "instagram-raw"
OUT = ROOT / "docs" / "instagram-api-catalog.csv"
SUMMARY = ROOT / "docs" / "instagram-api-summary.json"

USERS = ["renansantosreserva", "renansantosmbl"]
rows = []
summary = {}

for username in USERS:
    path = RAW / f"{username}-profile.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    user = payload.get("data", {}).get("user") or {}
    timeline = user.get("edge_owner_to_timeline_media") or {}
    edges = timeline.get("edges") or []
    page_info = timeline.get("page_info") or {}
    followers = (user.get("edge_followed_by") or {}).get("count")
    media_count = user.get("edge_owner_to_timeline_media", {}).get("count")

    for position, edge in enumerate(edges, start=1):
        node = edge.get("node") or {}
        caption_edges = ((node.get("edge_media_to_caption") or {}).get("edges") or [])
        caption = ""
        if caption_edges:
            caption = ((caption_edges[0].get("node") or {}).get("text") or "").strip()
        timestamp = node.get("taken_at_timestamp")
        taken_at = ""
        if timestamp:
            taken_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        rows.append({
            "profile": username,
            "position_in_api_page": position,
            "content_id": node.get("id", ""),
            "shortcode": node.get("shortcode", ""),
            "content_type": "video" if node.get("is_video") else "image_or_carousel",
            "product_type": node.get("product_type", ""),
            "taken_at_utc": taken_at,
            "caption": caption.replace("\n", " "),
            "like_count": (node.get("edge_media_preview_like") or {}).get("count", ""),
            "comment_count": (node.get("edge_media_to_comment") or {}).get("count", ""),
            "video_view_count": node.get("video_view_count", ""),
            "play_count": node.get("video_play_count", node.get("play_count", "")),
            "width": (node.get("dimensions") or {}).get("width", ""),
            "height": (node.get("dimensions") or {}).get("height", ""),
            "url": f"https://www.instagram.com/p/{node.get('shortcode', '')}/" if node.get("shortcode") else "",
        })

    summary[username] = {
        "followers": followers,
        "media_count_reported": media_count,
        "items_returned": len(edges),
        "page_info": page_info,
        "has_next_page": page_info.get("has_next_page"),
        "end_cursor": page_info.get("end_cursor"),
        "video_items_returned": sum(1 for row in rows if row["profile"] == username and row["content_type"] == "video"),
        "items_with_view_count": sum(1 for row in rows if row["profile"] == username and str(row["video_view_count"]).strip()),
    }

fieldnames = list(rows[0].keys()) if rows else ["profile", "content_id", "shortcode", "url"]
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
