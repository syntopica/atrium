"""Write one conversation's records, replacing whatever revision came before."""

import sqlite3
from collections.abc import Iterable

from atrium.record import Record

_INSERT = """
INSERT INTO records (
    record_id, event_id, conversation_id, source_sha256, provider, role, text,
    authored_at, workspace, title, event_index
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def write_conversation(
    connection: sqlite3.Connection, conversation_id: str, records: Iterable[Record]
) -> int:
    """Replace every record of ``conversation_id`` with ``records``.

    Replace rather than upsert, because the archive is canonical and this index
    is not allowed to disagree with it. An UPSERT-only path leaves superseded
    records searchable forever: a passage corrected in revision 2 still answers
    queries from revision 1, a deleted conversation is never deleted, and -- the
    case that matters most here -- a redaction added upstream never reaches the
    index. A fresh machine would then hold different memory from a long-lived
    one, which is the divergence this whole layering exists to prevent.

    The caller owns the transaction: reconciliation is only correct if the
    delete and the inserts commit together.
    """
    connection.execute("DELETE FROM records WHERE conversation_id = ?", (conversation_id,))
    rows = [
        (
            record.record_id,
            record.event_id,
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
        for record in records
    ]
    if rows:
        connection.executemany(_INSERT, rows)
    return len(rows)
