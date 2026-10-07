"""Validation of a tool's requested result count."""

from atrium.adapters.max_limit import MAX_LIMIT


def checked_limit(limit: int) -> int:
    """Return ``limit`` capped at ``MAX_LIMIT``; raise when it is below one."""
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    return min(limit, MAX_LIMIT)
