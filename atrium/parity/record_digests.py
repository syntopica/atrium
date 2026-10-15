"""Digest every record of an index by id."""

import hashlib
import sqlite3

from atrium.sql.load_sql import load_sql


def record_digests(connection: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    """Return record id to (provider, sha256 of its text), streaming the table."""
    return {
        record_id: (provider, hashlib.sha256(text.encode("utf-8")).hexdigest())
        for record_id, provider, text in connection.execute(load_sql("parity/record_texts"))
    }
