"""Load one archived conversation from the open file its stub was read from."""

import json
import os
from typing import Any


def conversation_at(descriptor: int, stub: dict[str, Any]) -> dict[str, Any]:
    """Return the conversation ``stub`` points at, checked to be the same one.

    ``os.pread`` reads at a position without moving a shared file offset, so
    pool threads can read one descriptor at once.
    """
    line = os.pread(descriptor, stub["length"], stub["offset"])
    conversation: dict[str, Any] = json.loads(line)
    if conversation.get("id") != stub["id"]:
        raise ValueError(f"archive offset {stub['offset']} no longer holds {stub['id']}")
    return conversation
