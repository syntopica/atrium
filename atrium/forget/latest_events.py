"""Read the forget ledger down to the latest event of each record."""

import fcntl
import json
from pathlib import Path
from typing import Any


def latest_events(ledger: Path) -> dict[str, dict[str, Any]]:
    """Return record id to its most recent event; an absent ledger holds none.

    A final line without its newline is a write a crash cut short, and is
    skipped: the append that wrote it never returned, so nothing relied on it.
    A malformed line anywhere else raises, because a ledger read past a damaged
    line would serve records the owner asked to forget. The read holds the
    ledger shared, so an ingest never takes a snapshot halfway through an
    append.
    """
    if not ledger.exists():
        return {}
    with ledger.open("rb") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        text = handle.read().decode("utf-8")
    lines = text.split("\n")
    if lines and lines[-1]:
        lines = lines[:-1]
    latest: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(lines, 1):
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{ledger}:{number} is not valid JSON") from error
        latest[event["record_id"]] = event
    return latest
