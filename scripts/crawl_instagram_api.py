from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
OUT = ROOT / 'docs' / 'instagram-api-catalog-full.json'
API_URLS = (
    'https://i.instagram.com/api/v1/users/web_profile_info/',
    'https://www.instagram.com/api/v1/users/web_profile_info/',
)
PROFILES = ('renansantosmbl', 'renansantosreserva')


def request_page(session, username, cursor=None):
    params = {'username': username}
    if cursor:
        params['after'] = cursor
    last = None
    for attempt in range(1, 7):
        for api_url in API_URLS:
            try:
                response = session.get(api_url, params=params, timeout=45)
                if response.status_code == 429:
                    last = RuntimeError(f'429 em {api_url}')
                    continue
                response.raise_for_status()
                payload = response.json()
                if payload.get('data', {}).get('user'):
                    return payload
                last = RuntimeError('Instagram retornou JSON sem data.user')
            except Exception as exc:
                last = exc
        time.sleep(min(3 ** (attempt - 1), 30) + random.uniform(0.5, 1.5))
    raise RuntimeError(f'Falha ao consultar {username}: {last}')


def parse_entry(node):
    shortcode = node.get('shortcode') or node.get('code')
    if not shortcode:
        return None
    is_video = bool(node.get('is_video'))
    return {
        'id': node.get('id'),
        'shortcode': shortcode,
        'url': f'https://www.instagram.com/reel/{shortcode}/' if is_video else f'https://www.instagram.com/p/{shortcode}/',
        'is_video': is_video,
        'media_type': node.get('media_type'),
        'taken_at_timestamp': node.get('taken_at_timestamp'),
        'display_url': node.get('display_url'),
        'thumbnail_src': node.get('thumbnail_src'),
        'caption': ((node.get('edge_media_to_caption') or {}).get('edges') or [{}])[0].get('node', {}).get('text', ''),
        'dimensions': node.get('dimensions'),
        'accessibility_caption': node.get('accessibility_caption'),
        'metadata_source': 'instagram_web_profile_info',
    }


def save(catalog):
    OUT.write_text(json.dumps({
        'collected_at': '2026-08-13',
        'scope': 'public Instagram profile API metadata; no login, posting or account mutation',
        'profiles': catalog,
    }, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-pages', type=int, default=0, help='0 means crawl until Instagram reports no next page')
    parser.add_argument('--profile', action='append', choices=PROFILES)
    parser.add_argument('--delay', type=float, default=0.7)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Instagram 290.0.0.0.109 Android',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'x-ig-app-id': '936619743392459',
        'Accept': 'application/json',
    })
    names = args.profile or list(PROFILES)
    catalog = []
    for username in names:
        entries = []
        seen = set()
        cursor = None
        pages = 0
        profile_user = {}
        while True:
            payload = request_page(session, username, cursor)
            user = payload['data']['user']
            profile_user = {
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'followers': (user.get('edge_followed_by') or {}).get('count'),
                'posts_count': (user.get('edge_owner_to_timeline_media') or {}).get('count'),
            }
            media = user.get('edge_owner_to_timeline_media') or {}
            for edge in media.get('edges', []):
                entry = parse_entry(edge.get('node', {}))
                key = (entry or {}).get('id') or (entry or {}).get('shortcode')
                if entry and key not in seen:
                    seen.add(key)
                    entries.append(entry)
            pages += 1
            page_info = media.get('page_info') or {}
            cursor = page_info.get('end_cursor')
            print(f'{username}: pagina={pages} itens={len(entries)} videos={sum(1 for e in entries if e["is_video"])} proxima={bool(page_info.get("has_next_page"))}', flush=True)
            if not page_info.get('has_next_page') or not cursor or (args.max_pages and pages >= args.max_pages):
                break
            time.sleep(max(0.0, args.delay) + random.uniform(0.0, 0.3))
        catalog.append({**profile_user, 'pages': pages, 'entries': entries})
        save(catalog)
    save(catalog)
    print('catalog_saved=', OUT)


if __name__ == '__main__':
    main()
