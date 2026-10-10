"""Read the vector-change counter, tolerating an index that predates it."""

import sqlite3

from atrium.sql.load_sql import load_sql


def read_dense_generation(connection: sqlite3.Connection) -> int | None:
    """Return the counter, or None when no writer has installed it yet."""
    try:
        row = connection.execute(load_sql("context/dense_generation")).fetchone()
    except sqlite3.OperationalError:
        return None
    return None if row is None else int(row[0])
