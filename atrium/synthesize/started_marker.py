"""Where a conversation marks that its synthesis has started but not finished."""

from pathlib import Path


def started_marker(partials: Path, conversation_id: str) -> Path:
    """Name the marker by conversation; partials themselves are named by content.

    A conversation whose map chunks are kept and acked no longer holds a worker
    result, so the pass's holding set forgot it and it waited for its turn in
    newest-first order. The marker is what remembers it.
    """
    return partials / "started" / conversation_id
