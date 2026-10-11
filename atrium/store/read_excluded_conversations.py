"""The conversations the ingest excluded as automation."""

import sqlite3

from atrium.sql.load_sql import load_sql


def read_excluded_conversations(connection: sqlite3.Connection) -> set[str]:
    """Return their ids; empty on an index older than the revision table."""
    try:
        rows = connection.execute(load_sql("store/read_excluded_conversations"))
        return {row[0] for row in rows}
    except sqlite3.OperationalError as error:
        if "no such table: conversation_revisions" not in str(error):
            raise
        return set()
