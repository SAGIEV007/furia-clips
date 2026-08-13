"""Shared cancellation signal for long-running local operations."""


class OperationCancelled(Exception):
    """Raised when the user requests a safe stop of the current operation."""
