"""Install the archive-generation table on an explicitly writable connection."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_archive_generation(connection: sqlite3.Connection) -> None:
    """Add the table without touching records or versions; idempotent."""
    connection.execute(load_sql("store/create_archive_generation"))
