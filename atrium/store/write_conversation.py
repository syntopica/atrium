"""Write one conversation's records, replacing whatever revision came before."""

import sqlite3
from collections.abc import Iterable

from atrium.record import Record

_COLUMNS = (
    "record_id, event_id, conversation_id, source_sha256, provider, role, text, "
    "authored_at, workspace, title, event_index"
)

# S608: the only interpolation is _COLUMNS, a literal above; values are bound.
_INSERT = f"""
INSERT INTO records ({_COLUMNS})
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""  # noqa: S608

_STORED = f"SELECT {_COLUMNS} FROM records WHERE conversation_id = ? ORDER BY record_id"  # noqa: S608


# A conversation reduced to no records writes zero rows, exactly as an
# unchanged one does. Callers count the two differently -- one is work not done,
# the other is a conversation that just disappeared from the index -- so the
# no-op says so rather than hiding behind a shared zero.
UNCHANGED = -1


def write_conversation(
    connection: sqlite3.Connection, conversation_id: str, records: Iterable[Record]
) -> int:
    """Replace every record of ``conversation_id`` with ``records``.

    Returns the number of records written, or ``UNCHANGED`` when the stored rows
    already equal ``records``.

    Replace rather than upsert, because the archive is canonical and this index
    is not allowed to disagree with it. An UPSERT-only path leaves superseded
    records searchable forever: a passage corrected in revision 2 still answers
    queries from revision 1, a deleted conversation is never deleted, and -- the
    case that matters most here -- a redaction added upstream never reaches the
    index. A fresh machine would then hold different memory from a long-lived
    one, which is the divergence this whole layering exists to prevent.

    The caller owns the transaction: reconciliation is only correct if the
    delete and the inserts commit together.

    A conversation whose stored rows already equal ``records`` is left alone
    rather than rewritten to the same values. That is not a speed
    optimisation: ``vectors.record_id`` cascades on delete, so rewriting an
    unchanged conversation destroys its embeddings, and a run that reconciles
    the whole archive would drop every vector in the index and pay the full
    re-embed again. Measured on this index: 19,198 vectors, hours of CPU, on
    every hourly refresh.
    """
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
    stored = connection.execute(_STORED, (conversation_id,)).fetchall()
    if stored == sorted(rows):
        return UNCHANGED
    connection.execute("DELETE FROM records WHERE conversation_id = ?", (conversation_id,))
    if rows:
        connection.executemany(_INSERT, rows)
    return len(rows)
