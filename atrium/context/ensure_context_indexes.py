"""Prepare derived context indexes only on an explicitly writable connection."""

import sqlite3

from atrium.context.context_index_specs import context_index_specs
from atrium.sql.load_sql import load_sql


def ensure_context_indexes(connection: sqlite3.Connection) -> None:
    """Add secondary indexes without changing records, schema versions, or sources."""
    for name, columns in context_index_specs().items():
        connection.execute(
            load_sql("context/create_context_index").format(name=name, columns=", ".join(columns))
        )
