"""Where an instance remembers which conversations an erasure removed."""

from pathlib import Path


def erased_conversations_file(state: Path) -> Path:
    """Return the instance's list of erased conversation ids, one per line."""
    return state / "erased-conversations.txt"
