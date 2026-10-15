"""Install the supersession table on an explicitly writable connection."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_supersessions(connection: sqlite3.Connection) -> None:
    """Add the table without touching records or versions.

    Additive and idempotent, like the dense counter: an existing index gains it
    on its next writable open, so no rebuild and no build-stamp bump.
    """
    connection.execute(load_sql("store/create_supersessions"))
