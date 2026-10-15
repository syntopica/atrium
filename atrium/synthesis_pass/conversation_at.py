"""Load one archived conversation by the byte offset of its line."""

import json
from pathlib import Path
from typing import Any


def conversation_at(archive: Path, offset: int) -> dict[str, Any]:
    """Return the conversation whose line starts at ``offset``.

    Opens the file per call, so pool threads never share a file position.
    """
    with archive.open("rb") as handle:
        handle.seek(offset)
        conversation: dict[str, Any] = json.loads(handle.readline())
    return conversation
