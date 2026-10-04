"""Read one record file, or nothing when it vanished or is not JSON."""

import json
from pathlib import Path
from typing import Any


def read_record_file(path: Path) -> dict[str, Any] | None:
    """Return the record, or ``None``: a reader never fails on one bad file."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None
