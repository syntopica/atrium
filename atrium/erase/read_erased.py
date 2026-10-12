"""Read the conversation ids an erasure removed from this instance."""

from pathlib import Path

from atrium.erase.erased_conversations_file import erased_conversations_file


def read_erased(state: Path) -> frozenset[str]:
    """Return every erased conversation id, or none when nothing was erased."""
    path = erased_conversations_file(state)
    if not path.is_file():
        return frozenset()
    return frozenset(path.read_text(encoding="utf-8").split())
