"""Install additive observing-host provenance on a writable derived index."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_record_hosts(connection: sqlite3.Connection) -> None:
    """Create the side table without rewriting existing records or vectors."""
    connection.execute(load_sql("store/create_record_hosts"))
