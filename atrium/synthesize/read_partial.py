"""A kept map-chunk synthesis, if this machine already holds it."""

import json
from pathlib import Path
from typing import Any


def read_partial(path: Path) -> dict[str, Any] | None:
    """Return the kept partial, or None when there is none or it is unreadable."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and isinstance(value.get("input"), dict) else None
