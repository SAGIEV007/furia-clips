"""Security helpers for local workspace file operations."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import Optional


class UnsafePathError(ValueError):
    """Raised when a requested path escapes the allowed root."""


def workspace_realpath(root: str) -> str:
    return os.path.realpath(os.path.abspath(root))


def is_within(root: str, candidate: str) -> bool:
    root_real = workspace_realpath(root)
    candidate_real = os.path.realpath(os.path.abspath(candidate))
    try:
        return os.path.commonpath([root_real, candidate_real]) == root_real
    except ValueError:
        return False


def safe_workspace_path(
    root: str,
    relative_path: str,
    *,
    allow_missing: bool = True,
    reject_symlink: bool = True,
) -> str:
    """Resolve a path below root and reject traversal or external symlinks."""

    if relative_path is None:
        raise UnsafePathError("Caminho não informado")
    raw = str(relative_path).replace("\\", os.sep)
    root_real = workspace_realpath(root)
    candidate = os.path.abspath(os.path.join(root_real, raw))
    if not is_within(root_real, candidate):
        raise UnsafePathError("Acesso fora do workspace")

    if reject_symlink:
        current = candidate
        if not allow_missing:
            parts = []
            while current != root_real and current:
                parts.append(current)
                current = os.path.dirname(current)
            parts.append(root_real)
        else:
            existing = candidate
            while not os.path.exists(existing) and existing != root_real:
                existing = os.path.dirname(existing)
            parts = []
            current = existing
            while current != root_real and current:
                parts.append(current)
                current = os.path.dirname(current)
            parts.append(root_real)
        for item in reversed(parts):
            if os.path.islink(item) and not is_within(root_real, os.path.realpath(item)):
                raise UnsafePathError("Symlink fora do workspace")

    if not allow_missing and not os.path.exists(candidate):
        raise FileNotFoundError(candidate)
    return candidate


def safe_filename(filename: str, extension: Optional[str] = None) -> str:
    """Return a filesystem-safe filename without directory components."""

    name = os.path.basename(str(filename or "")).strip()
    if not name or name in {".", ".."}:
        name = "arquivo"
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", name)
    name = name.strip(". ") or "arquivo"
    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        stem, _ = os.path.splitext(name)
        name = f"{stem[:120]}{ext.lower()}"
    return name[:140]


def unique_storage_name(original_name: str, extension: Optional[str] = None) -> str:
    safe = safe_filename(original_name, extension=extension)
    stem, ext = os.path.splitext(safe)
    return f"{stem[:90]}_{secrets.token_hex(6)}{ext}"
