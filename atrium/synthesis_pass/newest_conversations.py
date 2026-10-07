"""The archive's conversations, newest first."""

from pathlib import Path
from typing import Any

from atrium.ingest.read_archive import read_archive


def newest_conversations(archive: Path) -> list[dict[str, Any]]:
    """Order by last update, falling back to the start time."""
    return sorted(
        read_archive(archive),
        key=lambda c: c.get("updatedAt") or c.get("startedAt") or "",
        reverse=True,
    )
