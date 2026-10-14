"""Append events to the forget ledger in one durable write."""

import fcntl
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from atrium.forget.drop_cut_tail import drop_cut_tail
from atrium.forget.fsync_directory import fsync_directory


def append_ledger(ledger: Path, events: Sequence[dict[str, Any]]) -> None:
    """Write every event as one append, durable before returning.

    Holds the ledger exclusively, so a reader (``latest_events`` takes it
    shared) never sees half an append. A line a crash cut short is removed
    first: appending after it would glue the next event onto the fragment and
    turn a skipped line into a damaged one. A new file's directory entry is
    synced too, or a power cut could lose the whole ledger after the first
    ``forget --apply`` reported success.
    """
    if not events:
        return
    created = not ledger.exists()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    with ledger.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        drop_cut_tail(handle)
        handle.seek(0, os.SEEK_END)
        handle.write(payload.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    if created:
        fsync_directory(ledger.parent)
        fsync_directory(ledger.parent.parent)
