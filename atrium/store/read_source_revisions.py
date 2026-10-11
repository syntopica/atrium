"""Load every raw conversation's revision, for the synthesis ingest."""

import sqlite3

from atrium.sql.load_sql import load_sql
from atrium.store.revision import Revision


def read_source_revisions(connection: sqlite3.Connection) -> dict[str, Revision]:
    """Map each archived conversation id to its stored revision, all providers."""
    rows = connection.execute(load_sql("store/read_source_revisions"))
    return {row[0]: Revision(row[1], row[2], row[3]) for row in rows}
