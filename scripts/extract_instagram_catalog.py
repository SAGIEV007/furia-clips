from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs" / "instagram-raw"
OUT = ROOT / "docs" / "instagram-catalog.csv"
SUMMARY = ROOT / "docs" / "instagram-catalog-summary.json"

PROFILE_FILES = {
    "renansantosreserva": RAW / "renansantosreserva.html",
    "renansantosmbl": RAW / "renansantosmbl.html",
}

REEL_RE = re.compile(r"/reel/([A-Za-z0-9_-]+)/")
POST_RE = re.compile(r"/(?:p|tv)/([A-Za-z0-9_-]+)/")
COUNT_RE = re.compile(r"([\d.,]+)\s+(?:Followers|seguidores)")
POST_COUNT_RE = re.compile(r"([\d.,]+)\s+(?:Posts|publicaciones)")

rows = []
summary = {}

for username, path in PROFILE_FILES.items():
    html = path.read_text(encoding="utf-8", errors="replace")
    reel_ids = list(dict.fromkeys(REEL_RE.findall(html)))
    post_ids = list(dict.fromkeys(POST_RE.findall(html)))
    for position, reel_id in enumerate(reel_ids, start=1):
        rows.append({
            "profile": username,
            "content_type": "reel",
            "position_in_initial_html": position,
            "content_id": reel_id,
            "url": f"https://www.instagram.com/{username}/reel/{reel_id}/",
        })
    for position, post_id in enumerate(post_ids, start=1):
        rows.append({
            "profile": username,
            "content_type": "post_or_tv",
            "position_in_initial_html": position,
            "content_id": post_id,
            "url": f"https://www.instagram.com/p/{post_id}/",
        })
    summary[username] = {
        "file": str(path),
        "html_bytes": path.stat().st_size,
        "unique_reel_ids_in_initial_html": len(reel_ids),
        "unique_post_or_tv_ids_in_initial_html": len(post_ids),
        "has_show_more_posts": "Show more posts" in html or "Mostrar más publicaciones" in html,
        "has_cursor_marker": any(marker in html for marker in ("end_cursor", "has_next_page", "user_timeline")),
        "followers_text": COUNT_RE.findall(html)[:3],
        "posts_text": POST_COUNT_RE.findall(html)[:3],
    }

with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["profile", "content_type", "position_in_initial_html", "content_id", "url"])
    writer.writeheader()
    writer.writerows(rows)

SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"rows": len(rows), "summary": summary}, ensure_ascii=False, indent=2))
