"""When a record was written: its own stamp, else the file's mtime."""

from datetime import datetime
from typing import Any


def record_written_at(record: dict[str, Any], mtime: float) -> float:
    """Prefer ``synthesized_at``; records written before it existed use mtime."""
    stamp = record.get("synthesized_at")
    if isinstance(stamp, str):
        try:
            moment = datetime.fromisoformat(stamp)
        except ValueError:
            return mtime
        if moment.tzinfo is not None:
            return moment.timestamp()
    return mtime
