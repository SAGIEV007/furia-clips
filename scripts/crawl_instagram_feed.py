from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import requests

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
OUT = ROOT / 'docs' / 'instagram-feed-catalog-full.json'
PROFILES = {
    'renansantosmbl': '2334727603',
    'renansantosreserva': '24031008826',
}
API = 'https://i.instagram.com/api/v1/feed/user/{user_id}/'


def public_caption(item):
    caption = item.get('caption') or {}
    return caption.get('text', '') if isinstance(caption, dict) else ''


def parse_item(item, username):
    code = item.get('code')
    if not code:
        return None
    media_type = item.get('media_type')
    is_video = media_type == 2 or bool(item.get('video_versions')) or item.get('product_type') == 'clips'
    video_versions = item.get('video_versions') or []
    video_url = video_versions[0].get('url') if video_versions else None
    image_versions = item.get('image_versions2') or {}
    candidates = image_versions.get('candidates') or []
    thumbnail_url = candidates[0].get('url') if candidates else None
    return {
        'profile': username,
        'id': item.get('pk') or item.get('id'),
        'code': code,
        'url': f'https://www.instagram.com/reel/{code}/' if is_video else f'https://www.instagram.com/p/{code}/',
        'is_video': is_video,
        'media_type': media_type,
        'product_type': item.get('product_type'),
        'taken_at': item.get('taken_at'),
        'caption': public_caption(item),
        'like_count': item.get('like_count'),
        'comment_count': item.get('comment_count'),
        'video_duration': item.get('video_duration'),
        'video_url': video_url,
        'thumbnail_url': thumbnail_url,
        'width': item.get('original_width'),
        'height': item.get('original_height'),
        'metadata_source': 'instagram_public_feed_api',
    }


def request_page(session, username, user_id, max_id=None):
    params = {'count': 12}
    if max_id:
        params['max_id'] = max_id
    url = API.format(user_id=user_id)
    last = None
    for attempt in range(1, 6):
        try:
            response = session.get(url, params=params, timeout=45)
            if response.status_code == 429:
                last = RuntimeError('Instagram HTTP 429')
            else:
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict) and 'items' in payload:
                    return payload
                last = RuntimeError('Instagram retornou feed sem items')
        except Exception as exc:
            last = exc
        time.sleep(min(3 ** (attempt - 1), 30) + random.uniform(0.5, 1.5))
    raise RuntimeError(f'Falha ao consultar {username}: {last}')


def load_existing():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'collected_at': '2026-08-13', 'scope': 'public feed metadata; no login or account mutation', 'profiles': {}}


def save(catalog):
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', action='append', choices=tuple(PROFILES))
    parser.add_argument('--max-pages', type=int, default=0)
    parser.add_argument('--delay', type=float, default=1.0)
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Instagram 290.0.0.0.109 Android',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'x-ig-app-id': '936619743392459',
        'Accept': 'application/json',
    })
    catalog = load_existing()
    for username in args.profile or list(PROFILES):
        existing = catalog['profiles'].get(username, {})
        entries = existing.get('entries', [])
        seen = {entry.get('id') or entry.get('code') for entry in entries}
        max_id = existing.get('next_max_id')
        pages = existing.get('pages', 0)
        while True:
            payload = request_page(session, username, PROFILES[username], max_id)
            for item in payload.get('items', []):
                entry = parse_item(item, username)
                key = (entry or {}).get('id') or (entry or {}).get('code')
                if entry and key not in seen:
                    entries.append(entry)
                    seen.add(key)
            pages += 1
            max_id = payload.get('next_max_id')
            profile = payload.get('user') or {}
            catalog['profiles'][username] = {
                'username': username,
                'user_id': PROFILES[username],
                'followers': profile.get('follower_count'),
                'pages': pages,
                'entries': entries,
                'next_max_id': max_id,
                'more_available': bool(payload.get('more_available')),
            }
            save(catalog)
            videos = sum(1 for entry in entries if entry.get('is_video'))
            print(f'{username}: pagina={pages} total={len(entries)} videos={videos} proxima={bool(payload.get("more_available"))}', flush=True)
            if not payload.get('more_available') or not max_id or (args.max_pages and pages >= args.max_pages):
                break
            time.sleep(max(0.0, args.delay) + random.uniform(0.0, 0.5))
    print('catalog_saved=', OUT)


if __name__ == '__main__':
    main()
