"""Load the stored revisions of one provider in a single read."""

import sqlite3

from atrium.sql.load_sql import load_sql
from atrium.store.revision import Revision


def read_revisions(connection: sqlite3.Connection, provider: str) -> dict[str, Revision]:
    """Map conversation id to its revision; one query instead of one per conversation."""
    rows = connection.execute(load_sql("store/read_revisions"), (provider,))
    return {row[0]: Revision(row[1], row[2], row[3]) for row in rows}
