"""The record ids an index holds a vector for."""

import sqlite3

from atrium.sql.load_sql import load_sql


def vector_ids(connection: sqlite3.Connection) -> set[str]:
    """Return them as a set."""
    return {row[0] for row in connection.execute(load_sql("parity/vector_ids"))}
