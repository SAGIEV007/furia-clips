"""Lightweight JSON schema validators for Fúria Clips internal data."""

from __future__ import annotations

__all__ = [
    "ChubSnapshotValidationError",
    "ClipCandidateValidationError",
    "validate_chub_snapshot",
    "validate_clip_candidate",
]


class ChubSnapshotValidationError(ValueError):
    """Raised when a Chub snapshot payload is missing required fields."""


class ClipCandidateValidationError(ValueError):
    """Raised when a clip candidate dict is structurally invalid."""


def validate_chub_snapshot(payload: object) -> dict:
    """Validate a Chub MCP snapshot dict and return it when valid.

    Checks required top-level keys only to keep the validator cheap and
    dependency-free.
    """
    if not isinstance(payload, dict):
        raise ChubSnapshotValidationError("Snapshot must be a JSON object.")
    missing = {"account", "posts"}
    if not missing.issubset(payload):
        missing_fields = sorted(missing - payload.keys())
        raise ChubSnapshotValidationError(
            f"Snapshot missing required fields: {missing_fields}"
        )
    if not isinstance(payload.get("posts"), list):
        raise ChubSnapshotValidationError("Snapshot field 'posts' must be a list.")
    return payload


def validate_clip_candidate(clip: object) -> dict:
    """Validate a single clip candidate dict used by the selector/renderer.

    Required numeric fields must be finite numbers; optional fields are
    ignored when absent.
    """
    if not isinstance(clip, dict):
        raise ClipCandidateValidationError("Clip candidate must be a JSON object.")
    required_numeric = ("start", "end", "duration")
    errors = []
    for field in required_numeric:
        value = clip.get(field)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(f"{field} must be numeric")
            continue
        if not __import__("math").isfinite(numeric):
            errors.append(f"{field} must be finite")
    if errors:
        raise ClipCandidateValidationError(
            f"Invalid clip candidate: {'; '.join(errors)}"
        )
    return clip
