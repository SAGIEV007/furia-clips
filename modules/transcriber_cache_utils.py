import os
import time
from pathlib import Path

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'workspace', 'cache')


def _cache_entries():
    if not os.path.isdir(CACHE_DIR):
        return []
    entries = []
    for name in os.listdir(CACHE_DIR):
        if not name.startswith('transcription_') or not name.endswith('.json'):
            continue
        path = os.path.join(CACHE_DIR, name)
        try:
            stat = os.stat(path)
            entries.append((path, stat.st_size, stat.st_mtime))
        except OSError:
            pass
    return entries


def prune_cache(max_age_days=7, max_entries=200):
    now = time.time()
    entries = _cache_entries()
    entries.sort(key=lambda item: item[2], reverse=True)
    removed = 0
    for path, size, mtime in entries:
        age_days = (now - mtime) / 86400.0
        keep = age_days <= max_age_days
        if not keep:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
    remaining = len(_cache_entries())
    if remaining > max_entries:
        excess = remaining - max_entries
        for path, _, _ in entries[:excess]:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
    return {'removed': removed, 'remaining': len(_cache_entries())}


def get_cache_stats():
    entries = _cache_entries()
    now = time.time()
    total_size = sum(size for _, size, _ in entries)
    stale = [p for p, _, m in entries if (now - m) / 86400.0 > 7]
    return {
        'entries': len(entries),
        'total_bytes': total_size,
        'stale_entries': len(stale),
        'stale_bytes': sum(os.path.getsize(p) for p in stale if os.path.exists(p)),
    }
