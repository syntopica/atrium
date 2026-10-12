"""Where an instance keeps the lock that separates erasure from every writer."""

from pathlib import Path


def erase_lock_file(state: Path) -> Path:
    """Return the instance's erase lock, beside its index."""
    return state / "erase.lock"
