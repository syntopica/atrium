"""After ingesting a source's archive, the index holds exactly that archive."""

import json

from atrium.cli import main
from atrium.store.open_store import open_store


def _archive(path, conversations):
    lines = [json.dumps({"kind": "rocket-agents-conversation-export"})]
    lines += [json.dumps(c) for c in conversations]
    path.write_text("\n".join(lines))


def _conversation(conversation_id, text, source="test"):
    return {
        "id": conversation_id,
        "source": source,
        "provenance": {"contentSha256": f"sha-{conversation_id}"},
        "events": [
            {"id": "e1", "kind": "message", "role": "user", "text": text, "timestamp": None}
        ],
    }


def _conversation_ids(index):
    connection = open_store(index, read_only=True)
    rows = connection.execute("SELECT DISTINCT conversation_id FROM records ORDER BY 1").fetchall()
    connection.close()
    return [row[0] for row in rows]


def test_a_conversation_deleted_upstream_is_swept_on_reingest(tmp_path):
    """A conversation removed or redacted away upstream never appears in the
    new input, so per-conversation replacement alone can never delete it."""
    archive = tmp_path / "archive.jsonl"
    index = tmp_path / "index.sqlite3"
    _archive(archive, [_conversation("keep", "kept text"), _conversation("gone", "doomed text")])
    main(["--index", str(index), "ingest", str(archive)])
    _archive(archive, [_conversation("keep", "kept text")])
    main(["--index", str(index), "ingest", str(archive)])
    assert _conversation_ids(index) == ["keep"]


def test_partial_opts_out_of_the_sweep(tmp_path):
    archive = tmp_path / "archive.jsonl"
    index = tmp_path / "index.sqlite3"
    _archive(archive, [_conversation("keep", "kept text"), _conversation("gone", "doomed text")])
    main(["--index", str(index), "ingest", str(archive)])
    _archive(archive, [_conversation("keep", "kept text")])
    main(["--index", str(index), "ingest", str(archive), "--partial"])
    assert _conversation_ids(index) == ["gone", "keep"]


def test_the_sweep_only_touches_the_ingested_providers(tmp_path):
    archive = tmp_path / "a.jsonl"
    other = tmp_path / "b.jsonl"
    index = tmp_path / "index.sqlite3"
    _archive(archive, [_conversation("mine", "provider a text", source="alpha")])
    _archive(other, [_conversation("theirs", "provider b text", source="beta")])
    main(["--index", str(index), "ingest", str(archive)])
    main(["--index", str(index), "ingest", str(other)])
    # Re-ingesting alpha's archive must not sweep beta's conversations.
    main(["--index", str(index), "ingest", str(archive)])
    assert _conversation_ids(index) == ["mine", "theirs"]


def test_a_deleted_note_is_swept_on_reingest(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    index = tmp_path / "index.sqlite3"
    (notes / "keep.md").write_text("# Keep\n\nkept note")
    (notes / "gone.md").write_text("# Gone\n\ndoomed note")
    main(["--index", str(index), "ingest-notes", str(notes)])
    (notes / "gone.md").unlink()
    main(["--index", str(index), "ingest-notes", str(notes)])
    assert _conversation_ids(index) == ["keep.md"]
