"""The document the refresh job publishes when it finishes."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from atrium.doctor.newest_content_gap import newest_content_gap
from atrium.status.freshness import freshness
from atrium.status.indexed_synthesis_episodes import indexed_synthesis_episodes
from atrium.status.iso_utc import iso_utc
from atrium.status.population_counts import population_counts
from atrium.status.refresh_stamp_time import refresh_stamp_time
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION


def refresh_status(
    connection: sqlite3.Connection, archive: Path, stamp: Path, registry: Path, now: float
) -> dict[str, Any]:
    """Describe what the index holds and how old its inputs are, as counts and times.

    No record text, no paths: a dashboard stores and shows this document, so
    it carries only numbers, provider names, producer model names and instants.
    """
    by_source = dict(
        connection.execute("SELECT provider, count(*) FROM records GROUP BY provider ORDER BY 1")
    )
    newest = newest_content_gap(connection, now).detail.get("newest_authored_at")
    authored = datetime.fromisoformat(newest.replace("Z", "+00:00")).timestamp() if newest else None
    present = archive.exists()
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "writtenAt": iso_utc(now),
        "records": {"total": sum(by_source.values()), "bySource": by_source},
        "archive": {
            **freshness(archive.stat().st_mtime if present else None, now),
            "exists": present,
            "bytes": archive.stat().st_size if present else None,
        },
        "refresh": freshness(refresh_stamp_time(stamp), now),
        "content": freshness(authored, now),
        "populations": population_counts(registry, indexed_synthesis_episodes(connection)),
    }
