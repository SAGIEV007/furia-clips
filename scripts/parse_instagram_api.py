from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
API_DIR = ROOT / 'workspace' / 'instagram_api'
OUT = ROOT / 'docs' / 'instagram-api-catalog.json'

profiles = []
for source in sorted(API_DIR.glob('*.json')):
    payload = json.loads(source.read_text(encoding='utf-8'))
    user = payload.get('data', {}).get('user', {})
    media = user.get('edge_owner_to_timeline_media', {})
    entries = []
    for edge in media.get('edges', []):
        node = edge.get('node', {})
        shortcode = node.get('shortcode') or node.get('code')
        if not shortcode:
            continue
        entries.append({
            'id': node.get('id'),
            'shortcode': shortcode,
            'url': f'https://www.instagram.com/reel/{shortcode}/' if node.get('is_video') else f'https://www.instagram.com/p/{shortcode}/',
            'is_video': bool(node.get('is_video')),
            'media_type': node.get('media_type'),
            'taken_at_timestamp': node.get('taken_at_timestamp'),
            'display_url': node.get('display_url'),
            'thumbnail_src': node.get('thumbnail_src'),
            'caption': ((node.get('edge_media_to_caption') or {}).get('edges') or [{}])[0].get('node', {}).get('text', ''),
            'dimensions': node.get('dimensions'),
            'accessibility_caption': node.get('accessibility_caption'),
            'metadata_source': 'instagram_web_profile_info',
        })
    page_info = media.get('page_info', {})
    profiles.append({
        'username': user.get('username'),
        'full_name': user.get('full_name'),
        'followers': (user.get('edge_followed_by') or {}).get('count'),
        'posts_count': (user.get('edge_owner_to_timeline_media') or {}).get('count'),
        'first_page_count': len(entries),
        'has_next_page': page_info.get('has_next_page'),
        'end_cursor': page_info.get('end_cursor'),
        'entries': entries,
    })

OUT.write_text(json.dumps({'collected_at': '2026-08-13', 'profiles': profiles}, ensure_ascii=False, indent=2), encoding='utf-8')
for profile in profiles:
    print(profile['username'], 'posts=', profile['posts_count'], 'first_page=', profile['first_page_count'], 'videos=', sum(1 for e in profile['entries'] if e['is_video']), 'has_next=', profile['has_next_page'])
    print('cursor=', profile['end_cursor'])
