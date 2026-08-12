"""Local batch discovery and deduplication for video processing."""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from typing import Iterable, List


@dataclass
class BatchItem:
    path: str
    relative_path: str
    size: int
    modified_at: float
    content_hash: str
    status: str = "discovered"

    def as_dict(self) -> dict:
        return asdict(self)


def content_hash(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def scan_directory(root: str, extensions: Iterable[str], recursive: bool = True) -> List[BatchItem]:
    allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    root = os.path.realpath(root)
    paths = []
    if recursive:
        for current_root, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(current_root, d)))
            for name in sorted(files):
                paths.append(os.path.join(current_root, name))
    else:
        paths = [os.path.join(root, name) for name in sorted(os.listdir(root))]

    result = []
    seen_hashes = set()
    for path in paths:
        if not os.path.isfile(path) or os.path.islink(path):
            continue
        if os.path.splitext(path)[1].lower() not in allowed:
            continue
        digest = content_hash(path)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        stat = os.stat(path)
        result.append(
            BatchItem(
                path=path,
                relative_path=os.path.relpath(path, root),
                size=stat.st_size,
                modified_at=stat.st_mtime,
                content_hash=digest,
            )
        )
    return result


def build_manifest(root: str, extensions: Iterable[str]) -> dict:
    items = scan_directory(root, extensions)
    return {
        "root": os.path.realpath(root),
        "total": len(items),
        "items": [item.as_dict() for item in items],
    }
