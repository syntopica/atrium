"""Install the derived record counter on an explicitly writable connection."""

import sqlite3

from atrium.sql.load_sql import load_sql


def ensure_record_total(connection: sqlite3.Connection) -> None:
    """Seed existing records once, then count every later insert and delete."""
    connection.execute(load_sql("store/create_record_total"))
    connection.execute(load_sql("store/seed_record_total"))
    connection.execute(load_sql("store/create_record_total_insert_trigger"))
    connection.execute(load_sql("store/create_record_total_delete_trigger"))
