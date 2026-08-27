"""Write records into the index and keep both lexical lanes in step."""

import sqlite3
from collections.abc import Iterable

from atrium.record import Record

_INSERT = """
INSERT INTO records (
    record_id, conversation_id, source_sha256, provider, role, text,
    authored_at, workspace, title, event_index
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(record_id) DO UPDATE SET
    text = excluded.text,
    source_sha256 = excluded.source_sha256,
    authored_at = excluded.authored_at,
    title = excluded.title
"""

BATCH_SIZE = 1000


def write_records(connection: sqlite3.Connection, records: Iterable[Record]) -> int:
    """Insert or update ``records``, returning how many were written.

    The FTS tables are external-content, so they do not follow a plain UPSERT on
    their own. Rather than maintaining delete/insert triggers that can drift out
    of step with the base table, both lanes are rebuilt from `records` once at the
    end -- cheap, and it cannot leave the index in a state where a search sees a
    row the base table no longer has.
    """
    written = 0
    batch: list[tuple] = []
    for record in records:
        batch.append(
            (
                record.record_id,
                record.conversation_id,
                record.source_sha256,
                record.provider,
                record.role,
                record.text,
                record.authored_at,
                record.workspace,
                record.title,
                record.event_index,
            )
        )
        if len(batch) >= BATCH_SIZE:
            connection.executemany(_INSERT, batch)
            written += len(batch)
            batch.clear()
    if batch:
        connection.executemany(_INSERT, batch)
        written += len(batch)
    connection.commit()
    return written


def rebuild_lexical_lanes(connection: sqlite3.Connection) -> None:
    """Rebuild both FTS lanes from the base table."""
    connection.execute("INSERT INTO words(words) VALUES('rebuild')")
    connection.execute("INSERT INTO substrings(substrings) VALUES('rebuild')")
    connection.commit()
