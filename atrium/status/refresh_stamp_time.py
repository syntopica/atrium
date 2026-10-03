"""Read the refresh stamp as an epoch time, or nothing."""

import math
from pathlib import Path


def refresh_stamp_time(stamp: Path) -> float | None:
    """Return the recorded completion time, or None when absent or unreadable.

    Two writers share the stamp -- the refresh script writes whole seconds,
    ``record_refresh`` a float -- so both forms parse.
    """
    try:
        value = float(stamp.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if math.isfinite(value) else None
