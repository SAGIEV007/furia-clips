from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path('/home/ubuntu/furia-clips-rebuild')
OUT = ROOT / 'docs' / 'instagram-reels-catalog.json'
PROFILES = {
    'renansantosreserva': 'https://www.instagram.com/renansantosreserva/',
    'renansantosmbl': 'https://www.instagram.com/renansantosmbl/',
}

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
})

catalog = []
for profile, url in PROFILES.items():
    response = session.get(url, timeout=45)
    response.raise_for_status()
    source = html.unescape(response.text)
    profile_record = {
        'profile': profile,
        'profile_url': url,
        'http_status': response.status_code,
        'reels': [],
    }
    seen = set()
    for match in re.finditer(r'https?://(?:www\.)?instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)/?', source):
        reel_id = match.group(1)
        if reel_id in seen:
            continue
        seen.add(reel_id)
        start = max(0, match.start() - 3500)
        end = min(len(source), match.end() + 3500)
        context = source[start:end]
        context = re.sub(r'\\u003[cC]', '<', context)
        context = re.sub(r'\\u003[eE]', '>', context)
        context = re.sub(r'\\u0026', '&', context)
        context = re.sub(r'\\u0022', '"', context)
        date_match = re.search(r'(?:taken_at|datePublished|uploadDate)[^0-9]{0,20}(20\d{2}[-/]\d{2}[-/]\d{2})', context)
        caption_candidates = re.findall(r'(?:edge_media_to_caption|caption|description|title)[^{}]{0,120}?"text"\s*:\s*"(.*?)"', context, re.S)
        caption = ''
        if caption_candidates:
            caption = max((c for c in caption_candidates if len(c) > 10), key=len, default='')
            caption = bytes(caption, 'utf-8').decode('unicode_escape', errors='ignore')
        profile_record['reels'].append({
            'reel_id': reel_id,
            'reel_url': f'https://www.instagram.com/reel/{reel_id}/',
            'published_at_visible': date_match.group(1) if date_match else None,
            'caption_visible_candidate': caption[:2000],
            'metadata_source': 'public_profile_html',
            'needs_video_review': True,
        })
    catalog.append(profile_record)

OUT.write_text(json.dumps({
    'collected_at': '2026-08-13',
    'scope': 'public profile HTML only; no login, posting or account mutation',
    'profiles': catalog,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({profile['profile']: len(profile['reels']) for profile in catalog}, ensure_ascii=False))
