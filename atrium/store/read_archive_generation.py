"""Read the archive generation the index was last built from."""

import sqlite3

from atrium.sql.load_sql import load_sql


def read_archive_generation(connection: sqlite3.Connection) -> str | None:
    """Return it; ``None`` when none was recorded or the table predates it."""
    try:
        row = connection.execute(load_sql("store/read_archive_generation")).fetchone()
    except sqlite3.OperationalError as error:
        if "no such table: archive_generation" not in str(error):
            raise
        return None
    return row[0] if row else None
