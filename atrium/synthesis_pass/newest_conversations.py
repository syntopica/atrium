"""The archive's conversations, newest first, as stubs that point into it."""

import json
from pathlib import Path
from typing import Any

_STUB_FIELDS = ("id", "workspace", "startedAt", "updatedAt")


def newest_conversations(archive: Path) -> list[dict[str, Any]]:
    """Order by last update, falling back to the start time.

    Each stub keeps only what ordering and narrowing read, plus ``offset``, the
    byte where its line starts; ``conversation_at`` loads the whole conversation
    when a pass reaches it. Holding every parsed conversation instead cost the
    driver 14 GB resident for a 6.8 GB archive (2026-10-12), and under memory
    pressure that pushed the context service into swap.
    """
    stubs = []
    offset = 0
    with archive.open("rb") as handle:
        for line_number, line in enumerate(handle, start=1):
            start, offset = offset, offset + len(line)
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{archive}:{line_number} is not valid JSON") from error
            if payload.get("kind") == "rocket-agents-conversation-export":
                continue
            stubs.append({key: payload.get(key) for key in _STUB_FIELDS} | {"offset": start})
    return sorted(stubs, key=lambda c: c.get("updatedAt") or c.get("startedAt") or "", reverse=True)
