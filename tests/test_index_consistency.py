"""The index must never disagree with the archive it was derived from."""

import json
from dataclasses import replace

import pytest

from atrium.cli import main
from atrium.ingest.record_identity import record_identity
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store

LONG = "the canonical sentinel passage about retrieval"


def _conversation(conversation_id, events, sha="rev1"):
    return {
        "id": conversation_id,
        "source": "pi",
        "title": "t",
        "workspace": "[HOME]/p/x",
        "startedAt": "2026-08-01T00:00:00Z",
        "provenance": {"contentSha256": sha},
        "events": events,
    }


def _message(event_id, text, role="assistant"):
    return {"id": event_id, "kind": "message", "role": role, "text": text}


def _write_archive(path, conversations):
    lines = [
        json.dumps({"kind": "rocket-agents-conversation-export", "records": len(conversations)})
    ]
    lines += [json.dumps(c) for c in conversations]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_same_event_id_in_two_conversations_keeps_both(tmp_path):
    """Rocket-agents derives an event id from index and text alone, with no
    conversation in the hash, so identical text at the same position collides.
    Using it as a primary key lost 17 of 2,586 real OpenCode records and mixed
    one conversation's identity with another's revision hash."""
    archive, index = tmp_path / "a.jsonl", tmp_path / "i.sqlite3"
    _write_archive(
        archive,
        [
            _conversation("conv-a", [_message("shared", LONG)], sha="sha-a"),
            _conversation("conv-b", [_message("shared", LONG)], sha="sha-b"),
        ],
    )
    assert main(["--index", str(index), "ingest", str(archive)]) == 0

    connection = open_store(index, read_only=True)
    rows = connection.execute(
        "SELECT conversation_id, source_sha256 FROM records ORDER BY conversation_id"
    ).fetchall()
    assert rows == [("conv-a", "sha-a"), ("conv-b", "sha-b")]


def test_record_identity_is_deterministic_and_conversation_scoped():
    assert record_identity("c1", "e1") == record_identity("c1", "e1")
    assert record_identity("c1", "e1") != record_identity("c2", "e1")


def test_a_superseded_passage_stops_being_searchable(tmp_path):
    """The archive is canonical. A passage corrected upstream -- including one
    corrected by a widened redaction -- must not keep answering queries."""
    archive, index = tmp_path / "a.jsonl", tmp_path / "i.sqlite3"
    _write_archive(archive, [_conversation("c", [_message("e1", "obsolete sentinel value")])])
    main(["--index", str(index), "ingest", str(archive)])

    _write_archive(
        archive, [_conversation("c", [_message("e2", "current sentinel value")], sha="rev2")]
    )
    main(["--index", str(index), "ingest", str(archive)])

    connection = open_store(index, read_only=True)
    assert search_words(connection, "obsolete") == []
    assert [hit.record_id for hit in search_words(connection, "current")] != []


def test_a_malformed_archive_changes_nothing(tmp_path):
    """A mid-file failure must not leave a half-written index that looks populated."""
    archive, index = tmp_path / "a.jsonl", tmp_path / "i.sqlite3"
    archive.write_text(
        json.dumps(_conversation("c", [_message("e1", LONG)])) + "\nnot json\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        main(["--index", str(index), "ingest", str(archive)])

    connection = open_store(index, read_only=True)
    assert connection.execute("SELECT count(*) FROM records").fetchone()[0] == 0


def test_search_never_returns_a_row_whose_text_changed(tmp_path):
    """External-content FTS goes wrong rather than stale: a MATCH resolves stale
    row ids and then reads current text, so the old word returns the new row."""
    archive, index = tmp_path / "a.jsonl", tmp_path / "i.sqlite3"
    _write_archive(archive, [_conversation("c", [_message("e1", "old sentinel passage")])])
    main(["--index", str(index), "ingest", str(archive)])

    _write_archive(
        archive, [_conversation("c", [_message("e1", "new sentinel passage")], sha="rev2")]
    )
    main(["--index", str(index), "ingest", str(archive)])

    connection = open_store(index, read_only=True)
    assert search_words(connection, "old") == []
    assert [hit.text for hit in search_words(connection, "new")] == ["new sentinel passage"]


def test_rewriting_an_unchanged_conversation_keeps_its_vectors(tmp_path):
    """A no-op reconciliation must not cost the whole dense lane.

    vectors.record_id cascades on delete, so a write that deletes and reinserts
    identical rows silently drops every embedding for that conversation. Run
    hourly over the whole archive, that is the entire index re-embedded each
    time.
    """
    import numpy as np

    from atrium.record import Record
    from atrium.store.open_store import open_store
    from atrium.store.write_conversation import UNCHANGED, write_conversation
    from atrium.store.write_vectors import write_vectors

    record = Record(
        record_id="r1",
        event_id="e1",
        conversation_id="conv1",
        source_sha256="s1",
        provider="synthesis",
        role="synthesis",
        text="an episode",
        authored_at="2026-08-01T00:00:00Z",
        workspace="/home/me/p/atrium",
        title="t",
        event_index=0,
    )
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        assert write_conversation(connection, "conv1", [record]) == 1
        write_vectors(connection, [("r1", "s1")], np.zeros((1, 4), dtype=np.float32))
    assert connection.execute("SELECT count(*) FROM vectors").fetchone()[0] == 1

    with connection:
        assert write_conversation(connection, "conv1", [record]) == UNCHANGED
    assert connection.execute("SELECT count(*) FROM vectors").fetchone()[0] == 1

    # A real revision still replaces the record, and its stale vector goes.
    revised = replace(record, source_sha256="s2", text="a corrected episode")
    with connection:
        assert write_conversation(connection, "conv1", [revised]) == 1
    assert connection.execute("SELECT count(*) FROM vectors").fetchone()[0] == 0
    connection.close()


def test_a_locked_database_is_waited_out_not_raised(tmp_path):
    """An hourly ingest and a drip embed overlap by design; that is not an error."""
    import sqlite3

    from atrium.store.commit_with_retry import commit_with_retry

    index = tmp_path / "index.sqlite3"
    connection = open_store(index)
    attempts = []

    def write():
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise sqlite3.OperationalError("database is locked")
        return 7

    # The value comes back from the attempt that committed, so a caller can
    # total it without counting a rolled-back attempt twice.
    assert commit_with_retry(connection, write) == 7
    assert len(attempts) == 3

    # Anything that is not a lock is a real fault and must not be slept on.
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        commit_with_retry(
            connection,
            lambda: (_ for _ in ()).throw(sqlite3.OperationalError("no such table: nope")),
        )
    connection.close()


def test_an_unchanged_comparison_never_hides_a_real_change(tmp_path):
    """Deciding "unchanged" wrongly means the index disagreeing with the archive."""
    from atrium.record import Record
    from atrium.store.write_conversation import UNCHANGED, write_conversation

    def record(record_id, **overrides):
        fields = {
            "record_id": record_id,
            "event_id": "e",
            "conversation_id": "conv",
            "source_sha256": "s",
            "provider": "claude-code",
            "role": "user",
            "text": "t",
            "authored_at": None,
            "workspace": None,
            "title": None,
            "event_index": 0,
        }
        fields.update(overrides)
        return Record(**fields)

    connection = open_store(tmp_path / "index.sqlite3")

    def stored():
        return connection.execute("SELECT count(*) FROM records").fetchone()

    with connection:
        assert write_conversation(connection, "conv", [record("a"), record("b")]) == 2
    with connection:
        # Same rows, opposite order: the comparison sorts, so this is unchanged.
        assert write_conversation(connection, "conv", [record("b"), record("a")]) == UNCHANGED
    with connection:
        # Losing a record is a change even though the survivor is identical.
        assert write_conversation(connection, "conv", [record("a")]) == 1
    assert stored()[0] == 1
    with connection:
        # Gaining one is a change too.
        assert write_conversation(connection, "conv", [record("a"), record("c")]) == 2
    with connection:
        # A field moving off NULL is a change, not a tie.
        assert (
            write_conversation(connection, "conv", [record("a", workspace="/w"), record("c")]) == 2
        )
    with connection:
        # Emptying the conversation deletes it. That writes zero rows, exactly
        # as an unchanged conversation does, so the two must not share a value:
        # a conversation vanishing from the index is not work skipped.
        assert write_conversation(connection, "conv", []) == 0
    assert stored()[0] == 0
    connection.close()
