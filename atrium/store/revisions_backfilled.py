"""Whether the revision table covers every archived conversation."""

import sqlite3

from atrium.sql.load_sql import load_sql


def revisions_backfilled(connection: sqlite3.Connection) -> bool:
    """True once a full ingest has filled it; readers fall back until then."""
    return connection.execute(load_sql("store/read_revision_backfill")).fetchone() is not None
