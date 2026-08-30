"""Unified safe coercion helpers for bools and floats across Fúria Clips."""

from __future__ import annotations

__all__ = ["coerce_bool", "safe_float"]


def coerce_bool(value, default=False):
    """Interpret JSON, form-style, and legacy textual booleans consistently.

    Handles ``None``, native bools, numeric types, and common Portuguese/English
    string representations. Returns a real ``bool`` without truthiness surprises.
    """
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        try:
            return bool(value) and value == value  # filter NaN
        except (TypeError, ValueError):
            return bool(default)
    normalized = str(value or "").strip().lower()
    if not normalized:
        return bool(default)
    return normalized not in {"0", "false", "no", "não", "nao", "off", "disabled"}


def safe_float(value, default=0.0):
    """Return a finite float, falling back to *default* for missing/invalid input."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed if __import__("math").isfinite(parsed) else float(default)
