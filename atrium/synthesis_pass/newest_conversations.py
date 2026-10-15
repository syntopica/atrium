"""The archive's conversations, newest first, as stubs that point into it."""

import json
from typing import Any, BinaryIO

_STUB_FIELDS = ("id", "workspace", "startedAt", "updatedAt")


def newest_conversations(handle: BinaryIO, name: str) -> list[dict[str, Any]]:
    """Order by last update, falling back to the start time.

    Each stub keeps only what ordering and narrowing read, plus ``offset`` and
    ``length``, the bytes of its line in the file behind ``handle``;
    ``conversation_at`` loads it from that same open file when a pass reaches
    it. The caller keeps ``handle`` open for the whole pass: the refresh
    replaces the archive by rename, and an open file still reads the version
    these offsets describe. Holding every parsed conversation instead cost the
    driver 14 GB resident for a 6.8 GB archive (2026-10-12), and under memory
    pressure that pushed the context service into swap.
    """
    stubs = []
    offset = 0
    for line_number, line in enumerate(handle, start=1):
        start, offset = offset, offset + len(line)
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{name}:{line_number} is not valid JSON") from error
        if payload.get("kind") == "rocket-agents-conversation-export":
            continue
        stub = {key: payload.get(key) for key in _STUB_FIELDS}
        stubs.append(stub | {"offset": start, "length": len(line)})
    return sorted(stubs, key=lambda c: c.get("updatedAt") or c.get("startedAt") or "", reverse=True)
