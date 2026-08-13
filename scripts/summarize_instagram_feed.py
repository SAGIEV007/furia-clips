from __future__ import annotations

import json
from pathlib import Path

path = Path('/home/ubuntu/furia-clips-rebuild/docs/instagram-feed-catalog-full.json')
payload = json.loads(path.read_text(encoding='utf-8'))
for username, profile in payload.get('profiles', {}).items():
    entries = profile.get('entries', [])
    videos = [entry for entry in entries if entry.get('is_video')]
    dated = [entry for entry in entries if entry.get('taken_at')]
    likes = [entry.get('like_count') for entry in entries if isinstance(entry.get('like_count'), int)]
    print({
        'profile': username,
        'pages': profile.get('pages'),
        'entries': len(entries),
        'videos': len(videos),
        'more_available': profile.get('more_available'),
        'next_max_id': bool(profile.get('next_max_id')),
        'dated': len(dated),
        'likes_min': min(likes) if likes else None,
        'likes_max': max(likes) if likes else None,
    })
    print('last_codes=', [entry.get('code') for entry in entries[-5:]])
