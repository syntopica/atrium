"""Delete kept partials and started markers older than a bound."""

import time
from pathlib import Path

# Thirty days. A partial is reused by identical text in another conversation,
# so it cannot be deleted when its own episode records; age is the bound that
# keeps the shared ones useful while the directory stops growing.
MAX_AGE_SECONDS = 30 * 86400


def prune_partials(partials: Path, now: float | None = None) -> int:
    """Remove every partial and marker older than the bound; return how many."""
    cutoff = (time.time() if now is None else now) - MAX_AGE_SECONDS
    removed = 0
    for path in [*partials.glob("*.json"), *partials.glob("started/*")]:
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except FileNotFoundError:
            continue
    return removed
