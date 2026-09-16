"""A short page is the last page: the lane must not pay for the one after it."""

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


def test_a_short_page_ends_the_paging(tmp_path):
    """The statement costs a full execution per page, and against the curated
    scope that measured 0.31s on the live index -- paid twice for a query whose
    every hit arrived in the first page."""
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(connection, "c", [_record("note", "vault rotation runbook")])
    statements = []
    connection.set_trace_callback(statements.append)
    hits = lexical_hits(connection, "vault rotation", 8, "words", curated=True)
    connection.set_trace_callback(None)
    assert [hit.record_id for hit in hits] == ["note"]
    assert sum("WITH eligible" in statement for statement in statements) == 1
