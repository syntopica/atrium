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
    assert [r.event_id for r in to_records(conversation)] == ["keep", "keep2"]


def test_records_carry_the_revision_they_came_from():
    """Citations resolve to a revision hash, never to a byte offset."""
    (record,) = to_records(_conversation([_message("assistant", LONG)]))
    assert record.event_id == "e1"
    assert record.source_sha256 == "abc123"
    assert record.conversation_id == "conv-1"
    assert record.authored_at == "2026-08-01T00:00:00Z"


def test_a_conversation_without_provenance_is_refused():
    with pytest.raises(ValueError, match="provenance"):
        list(to_records({"id": "c", "events": []}))


def test_short_messages_are_kept_because_they_carry_facts():
    """Measured over 882 real messages, a 120-character floor would discard 43.4%
    of them -- including "63 tests verdes" and "Commit hecho. Deploy a server-a."."""
    conversation = _conversation(
        [
            _message("assistant", "63 tests verdes.", "fact1"),
            _message("assistant", "YAML roto: dos puntos dentro de scalar plano.", "fact2"),
            _message("user", "Arregla todo y guarda los findings en brain", "fact3"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["fact1", "fact2", "fact3"]


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
    assert [r.event_id for r in to_records(conversation)] == ["keep"]


def test_rendered_tool_calls_and_their_results_are_not_records():
    """Older Claude Code exports render a tool_use as `tool: <Name>` from the
    assistant and its result as the next user message, unmarked: 1.45M of the
    1.85M raw records on 2026-10-14. Parallel calls render every invocation
    before any result, so the user's next real prompt must survive the run."""
    conversation = _conversation(
        [
            _message("user", "Arregla el test del slug", "prompt"),
            _message("assistant", "Miro los ficheros.", "prose"),
            _message("assistant", "tool: Bash", "call1"),
            _message("assistant", 'tool: Read\n{"file_path": "a.ts"}', "call2"),
            _message("user", "Exit code 1\nbuildCanonicalPath.ts", "result1"),
            _message("user", "1\timport { describe } from 'vitest'", "result2"),
            _message("assistant", "El test falla por el import.", "answer"),
            _message("user", "vale, arreglalo y haz commit", "next"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prompt", "prose", "answer", "next"]


def test_an_empty_tool_result_still_settles_its_call():
    conversation = _conversation(
        [
            _message("assistant", "tool: Bash", "call"),
            _message("user", "", "empty-result"),
            _message("user", "Ahora despliega a staging", "prompt"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prompt"]


def test_assistant_prose_closes_a_tool_round_whose_result_never_arrived():
    conversation = _conversation(
        [
            _message("assistant", "tool: Bash", "call"),
            _message("assistant", "Lo dejo aqui, el comando no respondio.", "prose"),
            _message("user", "Prueba otra vez con timeout", "prompt"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prose", "prompt"]


def test_prose_that_mentions_a_tool_is_not_a_rendered_call():
    conversation = _conversation(
        [
            _message("assistant", "tool: Bash is what I would use here, but no.", "prose"),
            _message("user", "tool: Read the README first", "prompt"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prose", "prompt"]


def test_calls_rendered_at_the_end_of_prose_keep_the_prose_and_drop_their_results():
    conversation = _conversation(
        [
            _message("assistant", "Purgo la cache.\ntool: Bash\ntool: Bash", "prose"),
            _message("user", "cpanel-deploy.sh", "result1"),
            _message("user", "HTTP/2 200", "result2"),
            _message("user", "Ya no sale la pagina vieja", "prompt"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prose", "prompt"]


def test_a_result_archived_with_its_own_role_settles_the_rendered_call():
    """Since scribe 199f393 new results arrive as `role: tool`; dropped by the
    role rule, they must still settle the call, or the next prompt is lost."""
    conversation = _conversation(
        [
            _message("assistant", "tool: Bash", "call"),
            {"id": "result", "kind": "message", "role": "tool", "text": "ok"},
            _message("user", "Ahora sube el cambio a main", "prompt"),
        ]
    )
    assert [r.event_id for r in to_records(conversation)] == ["prompt"]
