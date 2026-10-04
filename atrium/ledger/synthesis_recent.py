"""The `synthesis recent` document: newest records, tokens per day, passes."""

import heapq
from pathlib import Path
from typing import Any

from atrium.ledger.daily_token_totals import daily_token_totals
from atrium.ledger.read_record_file import read_record_file
from atrium.ledger.record_metadata import record_metadata
from atrium.ledger.record_written_at import record_written_at
from atrium.ledger.scan_record_files import scan_record_files
from atrium.ledger.synthesis_passes import synthesis_passes
from atrium.status.iso_utc import iso_utc
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION


def synthesis_recent(registry: Path, now: float, limit: int, days: int) -> dict[str, Any]:
    """Describe the newest ``limit`` records and the last ``days`` of spend.

    The registry is listed once and only the newest files and the window's
    files are opened. Every field is an identity, a recipe value, a count or
    an instant: the synthesized text is read by ``synthesis show`` alone.
    """
    entries = scan_record_files(registry)
    recent = []
    for mtime, path in heapq.nlargest(limit, entries, key=lambda entry: entry[0]):
        record = read_record_file(path)
        if record is not None:
            recent.append(record_metadata(record, record_written_at(record, mtime)))
    passes = synthesis_passes(registry, now, 10)
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "writtenAt": iso_utc(now),
        "records": len(entries),
        "recent": recent,
        "daily": daily_token_totals(entries, now, days),
        "lastPass": passes["lastPass"],
        "unsuccessfulStreak": passes["unsuccessfulStreak"],
        "progress": passes["progress"],
    }
