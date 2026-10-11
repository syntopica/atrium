"""Empty the synthesis partials cache, unfinished writes included."""

from pathlib import Path


def clear_partials(partials: Path) -> int:
    """Delete every file under ``partials``; return how many.

    Partials are a cache keyed by input text, so which ones hold erased text
    cannot be told from their names, and an interrupted ``keep_partial`` leaves
    its ``.tmp-*`` file behind with the same content. All of it goes.
    """
    removed = 0
    if not partials.is_dir():
        return removed
    for path in sorted(partials.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
            removed += 1
    return removed
