"""The supersessions the served registry records declare."""

from collections.abc import Iterable
from typing import Any

from atrium.ingest.record_identity import record_identity


def supersession_rows(records: Iterable[dict[str, Any]]) -> list[tuple[str, str, str | None]]:
    """Return ``(superseded record, superseding record, when)`` for every declaration.

    When two statements supersede the same record, the later one names it: a
    reader following the mark should land on what is current, not on an
    intermediate correction.
    """
    latest: dict[str, tuple[str, str | None]] = {}
    for record in records:
        targets = record.get("supersedes") or []
        if not targets:
            continue
        by = record_identity(f"synthesis/{record['conversation_id']}", record["episode_id"])
        at = record.get("authored_at")
        for target in targets:
            current = latest.get(target)
            if current is None or (at or "") > (current[1] or ""):
                latest[target] = (by, at)
    return sorted((target, by, at) for target, (by, at) in latest.items())
