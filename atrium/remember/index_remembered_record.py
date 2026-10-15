"""Index one remembered statement now, instead of at the next refresh."""

import sqlite3
from typing import TYPE_CHECKING, Any

from atrium.ingest.rows_sha256 import rows_sha256
from atrium.ingest.supersession_rows import supersession_rows
from atrium.ingest.to_synthesis_records import to_synthesis_records
from atrium.sql.load_sql import load_sql
from atrium.store.revision import Revision
from atrium.store.upsert_revision import upsert_revision
from atrium.store.write_conversation import write_conversation
from atrium.store.write_vectors import write_vectors

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder


def index_remembered_record(
    connection: sqlite3.Connection, record: dict[str, Any], embedder: "ContextEmbedder | None"
) -> str:
    """Write the record's row, revision, supersessions and vector; return its record id.

    Exactly what the next ``ingest-synthesis`` would write, revision included,
    so that pass finds it unchanged and leaves its vector alone. One attempt
    only: a statement an agent makes must not wait out a refresh's lock for
    twenty minutes, and the registry already holds it, so a locked index costs
    nothing but the delay until the next refresh. The caller reports that.
    """
    workspace = record.get("workspace")
    rows = list(to_synthesis_records(record, workspace))
    if not rows:
        raise ValueError("the statement produced no indexable text")
    conversation_id = rows[0].conversation_id
    with connection:
        write_conversation(connection, conversation_id, rows)
        upsert_revision(
            connection,
            conversation_id,
            "synthesis",
            Revision(rows_sha256(rows), workspace, "indexed"),
        )
        connection.executemany(load_sql("store/insert_supersession"), supersession_rows([record]))
    if embedder is not None:
        matrix = embedder.embed([row.text for row in rows])
        with connection:
            write_vectors(connection, [(row.record_id, row.source_sha256) for row in rows], matrix)
    return rows[0].record_id
