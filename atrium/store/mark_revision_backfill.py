"""Record that a full ingest has written every archived conversation's revision."""

import sqlite3
from datetime import UTC, datetime

from atrium.sql.load_sql import load_sql


def mark_revision_backfill(connection: sqlite3.Connection) -> None:
    """Stamp the time; only a swept, complete pass may call this."""
    connection.execute(load_sql("store/mark_revision_backfill"), (datetime.now(UTC).isoformat(),))
