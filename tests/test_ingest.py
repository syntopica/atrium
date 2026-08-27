"""Ingest turns a canonical archive into records, and drops what is not conversation."""

import json

import pytest

from atrium.ingest.read_archive import read_archive
from atrium.ingest.to_records import to_records


def _conversation(events):
    return {
        "id": "conv-1",
        "source": "pi",
        "title": "a title",
        "workspace": "[HOME]/p/x",
        "startedAt": "2026-08-01T00:00:00Z",
        "provenance": {"contentSha256": "abc123"},
        "events": events,
    }


def _message(role, text, event_id="e1"):
    return {"id": event_id, "kind": "message", "role": role, "text": text}


LONG = "x" * 200


def test_manifest_line_is_not_a_conversation(tmp_path):
    archive = tmp_path / "a.jsonl"
    archive.write_text(
        json.dumps({"kind": "rocket-agents-conversation-export", "records": 1})
        + "\n"
        + json.dumps(_conversation([_message("user", LONG)]))
        + "\n",
        encoding="utf-8",
    )
    assert [c["id"] for c in read_archive(archive)] == ["conv-1"]


def test_a_malformed_line_raises_rather_than_half_ingesting(tmp_path):
    """A partially readable archive must not produce an index that looks complete."""
    archive = tmp_path / "a.jsonl"
    archive.write_text('{"id": "conv-1"}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        list(read_archive(archive))


def test_tool_events_and_acknowledgements_are_not_records():
    """The system this replaces indexed both: 251,568 tool-output records (18.8%)
    and 101,967 acknowledgements (7.6%), all competing with prose in every search."""
    conversation = _conversation(
        [
            _message("user", LONG, "keep"),
            _message("user", "ok", "ack"),
            _message("assistant", LONG, "keep2"),
            {"id": "tool", "kind": "tool_result", "role": "user", "text": LONG},
            {"id": "sys", "kind": "message", "role": "unknown", "text": LONG},
        ]
    )
    assert [r.record_id for r in to_records(conversation)] == ["keep", "keep2"]


def test_records_carry_the_revision_they_came_from():
    """Citations resolve to a revision hash, never to a byte offset."""
    (record,) = to_records(_conversation([_message("assistant", LONG)]))
    assert record.source_sha256 == "abc123"
    assert record.conversation_id == "conv-1"
    assert record.authored_at == "2026-08-01T00:00:00Z"


def test_a_conversation_without_provenance_is_refused():
    with pytest.raises(ValueError, match="provenance"):
        list(to_records({"id": "c", "events": []}))


def test_short_messages_are_kept_because_they_carry_facts():
    """Measured over 882 real messages, a 120-character floor would discard 43.4%
    of them -- including "63 tests verdes" and "Commit hecho. Deploy a nova."."""
    conversation = _conversation(
        [
            _message("assistant", "63 tests verdes.", "fact1"),
            _message("assistant", "YAML roto: dos puntos dentro de scalar plano.", "fact2"),
            _message("user", "Arregla todo y guarda los findings en brain", "fact3"),
        ]
    )
    assert [r.record_id for r in to_records(conversation)] == ["fact1", "fact2", "fact3"]


def test_bare_acknowledgements_are_dropped():
    """The same measurement puts this pattern at 1.0% of messages."""
    conversation = _conversation(
        [
            _message("user", "vale", "a1"),
            _message("user", "adelante!", "a2"),
            _message("user", "sí, gracias", "keep"),
            _message("assistant", "Listo.", "a3"),
        ]
    )
    assert [r.record_id for r in to_records(conversation)] == ["keep"]
