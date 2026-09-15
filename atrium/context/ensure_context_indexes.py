"""Prepare derived context indexes only on an explicitly writable connection."""

import sqlite3

from atrium.context.context_index_specs import context_index_specs


def ensure_context_indexes(connection: sqlite3.Connection) -> None:
    """Add secondary indexes without changing records, schema versions, or sources."""
    for name, columns in context_index_specs().items():
        connection.execute(f"CREATE INDEX IF NOT EXISTS {name} ON records ({', '.join(columns)})")
