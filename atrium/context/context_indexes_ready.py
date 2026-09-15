"""Inspect context acceleration metadata without changing the index."""

import sqlite3

from atrium.context.context_index_specs import context_index_specs


def context_indexes_ready(connection: sqlite3.Connection) -> bool:
    """Require both covering indexes with their expected ordered columns."""
    for name, columns in context_index_specs().items():
        actual = tuple(row[2] for row in connection.execute(f"PRAGMA index_info({name})"))
        if actual != columns:
            return False
    return True
