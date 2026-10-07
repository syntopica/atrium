"""The `synthesis show` document: one record's metadata and its content."""

import re
from pathlib import Path
from typing import Any

from atrium.ledger.read_record_file import read_record_file
from atrium.ledger.record_metadata import record_metadata
from atrium.ledger.record_written_at import record_written_at
from atrium.status.iso_utc import iso_utc
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION
from atrium.synthesize.record_path import record_path

JOB_KEY = re.compile(r"^[0-9a-f]{32}$")


def synthesis_record_detail(registry: Path, job_key: str, now: float) -> dict[str, Any] | None:
    """Return the record's metadata plus ``content``, or ``None`` if absent.

    ``content`` holds the synthesized title, summary, facts and open ends:
    text about the operator's work, marked so a reader can gate it. The key
    must be a registry key, so no argument can name a path.
    """
    if JOB_KEY.match(job_key) is None:
        return None
    path = record_path(registry, job_key)
    record = read_record_file(path)
    if record is None:
        return None
    raw = record.get("output")
    output: dict[str, Any] = raw if isinstance(raw, dict) else {}
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "writtenAt": iso_utc(now),
        "record": record_metadata(record, record_written_at(record, path.stat().st_mtime)),
        "content": {
            "title": output.get("title") or "",
            "summary": output.get("summary") or "",
            "facts": list(output.get("facts") or []),
            "openEnds": list(output.get("open_ends") or []),
        },
    }
