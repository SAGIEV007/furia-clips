"""JSON I/O helpers with consistent error handling for Fúria Clips."""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["read_json_file", "write_json_file"]


class JsonIOError(ValueError):
    """Raised when a JSON file cannot be read or written safely."""


def read_json_file(path: str | Path, *, default=None):
    """Read a JSON file and return the parsed object, or `default` on failure."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return default


def write_json_file(path: str | Path, payload, *, ensure_ascii=False, indent=2):
    """Write a JSON file atomically-ish: parent dirs are created automatically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(
            json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent) + "\n",
            encoding="utf-8",
        )
        return target
    except OSError as exc:
        raise JsonIOError(f"Failed to write JSON to {path}: {exc}") from exc
