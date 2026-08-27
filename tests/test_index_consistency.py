"""The index must never disagree with the archive it was derived from."""

import json

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
