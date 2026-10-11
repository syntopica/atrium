"""Install the per-conversation revision table on an explicitly writable connection."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_conversation_revisions(connection: sqlite3.Connection) -> None:
    """Add the table empty; the next full ingest fills it.

    Additive and idempotent like the other derived tables, so no rebuild and no
    build-stamp bump. It is never seeded from the rows already indexed: a stored
    row is not proof of what the archive holds now, and a revision taken from it
    would let a stale or since-redacted row pass the fast path forever.
    """
    connection.execute(load_sql("store/create_conversation_revisions"))
    connection.execute(load_sql("store/create_revision_provider_index"))
    connection.execute(load_sql("store/create_revision_disposition_index"))
    connection.execute(load_sql("store/create_revision_backfill"))
