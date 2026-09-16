"""One statement per pass: the lane streams the match, it does not page it."""

from atrium.context.lexical_hits import lexical_hits
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _record(record_id, text):
    return Record(
        record_id=record_id,
        event_id=record_id,
        conversation_id="c",
        source_sha256="s",
        provider="test",
        role="note",
        text=text,
        authored_at="2026-09-16T00:00:00Z",
        workspace=None,
        title=None,
        event_index=0,
    )


def test_the_statement_runs_once_however_many_rows_match(tmp_path):
    """Paging re-executed the whole sorted statement per page -- measured at
    0.31s a page against the curated scope on the live index -- and asked for the
    page after a short one. A rank-ordered read asks once and stops reading."""
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        records = [_record(f"note-{number}", "vault rotation runbook") for number in range(500)]
        write_conversation(connection, "c", records)
    statements = []
    connection.set_trace_callback(statements.append)
    hits = lexical_hits(connection, "vault rotation", 8, "words", curated=True)
    connection.set_trace_callback(None)
    assert len(hits) == 8
    assert sum("WITH eligible" in statement for statement in statements) == 1
