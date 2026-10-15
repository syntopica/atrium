"""Record which archive generation the index was built from."""

import sqlite3

from atrium.sql.load_sql import load_sql


def write_archive_generation(connection: sqlite3.Connection, generation_id: str | None) -> None:
    """Store ``generation_id``, or clear it for an archive that names none."""
    if generation_id is None:
        connection.execute(load_sql("store/delete_archive_generation"))
        return
    connection.execute(load_sql("store/write_archive_generation"), {"generation_id": generation_id})
