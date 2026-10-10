"""Install the vector-change counter on an explicitly writable connection."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_dense_generation(connection: sqlite3.Connection) -> None:
    """Add the counter and its triggers without touching records or versions.

    Additive and idempotent, like the context indexes: an existing index gains
    it on its next writable open, so no rebuild and no build-stamp bump.
    """
    connection.execute(load_sql("store/create_dense_generation"))
    connection.execute(load_sql("store/seed_dense_generation"))
    connection.execute(load_sql("store/create_dense_generation_insert_trigger"))
    connection.execute(load_sql("store/create_dense_generation_delete_trigger"))
