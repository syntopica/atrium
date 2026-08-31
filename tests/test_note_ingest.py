"""Curated notes become records with the same convergence guarantees."""

import re

from atrium.ingest.read_notes import read_notes
from atrium.ingest.to_note_records import to_note_records
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _note(text, path="topics/example.md"):
    import hashlib

    return {"path": path, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}


def test_chunking_is_deterministic_across_machines():
    note = _note("# Title\n\nintro\n\n## Section\n\nbody text here")
    first = list(to_note_records(note))
    second = list(to_note_records(note))
    assert [r.record_id for r in first] == [r.record_id for r in second]
    assert all(r.role == "note" for r in first)
    assert all(r.provider == "brain" for r in first)


def test_sections_split_on_headings():
    note = _note("# Title\n\nintro\n\n## One\n\nfirst body\n\n## Two\n\nsecond body")
    texts = [r.text for r in to_note_records(note)]
    assert any("first body" in t for t in texts)
    assert any("second body" in t for t in texts)
    assert not any("first body" in t and "second body" in t for t in texts)


def test_editing_a_note_replaces_its_records(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(
            connection, "n.md", to_note_records(_note("# N\n\nthe obsolete sentinel", "n.md"))
        )
    with connection:
        write_conversation(
            connection, "n.md", to_note_records(_note("# N\n\nthe current sentinel", "n.md"))
        )
    assert search_words(connection, "obsolete") == []
    assert len(search_words(connection, "current")) == 1
    connection.close()


def test_an_unbroken_oversized_paragraph_is_still_bounded():
    """Paragraph packing alone let a 17,999-character table through, and past
    the embedder's truncation the tail contributes nothing to the vector."""
    note = _note("# T\n\n" + "x" * 5000)
    lengths = [len(r.text) for r in to_note_records(note)]
    assert max(lengths) <= 2000
    assert sum(lengths) >= 5000


def test_read_notes_skips_hidden_directories_and_non_markdown(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.md").write_text("hidden")
    (tmp_path / "binary.pdf").write_bytes(b"%PDF")
    (tmp_path / "real.md").write_text("# Real\n\ncontent")
    notes = list(read_notes(tmp_path))
    assert [n["path"] for n in notes] == ["real.md"]


def test_read_notes_excludes_named_directories(tmp_path):
    """A curated tree often carries a raw-material subtree (brain's sources/
    holds 10,934 converted third-party files against ~230 curated notes);
    the vector budget covers only the curated layer."""
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "raw.md").write_text("third-party dump")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.md").write_text("dependency readme")
    (tmp_path / "curated.md").write_text("# Curated\n\nnote")
    notes = list(read_notes(tmp_path, exclude=("sources",)))
    assert [n["path"] for n in notes] == ["curated.md"]


def test_synthesis_records_inherit_the_source_conversation_workspace(tmp_path):
    """A synthesis record with no workspace is invisible to project recall."""
    from atrium.ingest.conversation_workspaces import conversation_workspaces
    from atrium.ingest.to_synthesis_records import to_synthesis_records
    from atrium.record import Record
    from atrium.store.open_store import open_store
    from atrium.store.write_conversation import write_conversation

    def event(index, conversation_id, workspace):
        return Record(
            record_id=f"{conversation_id}-{index}",
            event_id=f"e{index}",
            conversation_id=conversation_id,
            source_sha256=f"s{index}",
            provider="claude-code",
            role="user",
            text=f"turn {index}",
            authored_at="2026-08-01T00:00:00Z",
            workspace=workspace,
            title=None,
            event_index=index,
        )

    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(connection, "conv1", [event(0, "conv1", "/home/me/p/atrium")])
        # A conversation the exporter could not place has no workspace at all;
        # its synthesis must stay unscoped rather than borrow someone else's.
        write_conversation(connection, "conv2", [event(0, "conv2", None)])
    workspaces = conversation_workspaces(connection)
    connection.close()

    assert workspaces == {"conv1": "/home/me/p/atrium"}

    def record(conversation_id):
        return {
            "conversation_id": conversation_id,
            "episode_id": f"ep-{conversation_id}",
            "job_key": f"k-{conversation_id}",
            "authored_at": "2026-08-01T00:00:00Z",
            "output": {"title": "t", "summary": "s", "facts": ["f"], "open_ends": []},
        }

    scoped = list(to_synthesis_records(record("conv1"), workspaces.get("conv1")))
    unscoped = list(to_synthesis_records(record("conv2"), workspaces.get("conv2")))
    assert [row.workspace for row in scoped] == ["/home/me/p/atrium"]
    assert [row.workspace for row in unscoped] == [None]


def test_no_ingest_ever_reports_a_negative_record_count(tmp_path, capsys):
    """UNCHANGED is a sentinel, not a count: summed as one, a total goes wrong."""
    from atrium.cli import main

    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "one.md").write_text("# One\n\nA curated note.\n")
    index = tmp_path / "index.sqlite3"

    assert main(["--index", str(index), "ingest-notes", str(notes)]) == 0
    first = capsys.readouterr().out
    assert "1 records written" in first

    # Second pass over identical notes: nothing written, nothing negative.
    assert main(["--index", str(index), "ingest-notes", str(notes)]) == 0
    second = capsys.readouterr().out
    assert "0 records written" in second
    assert "1 notes unchanged" in second
    # Not a bare `"-1" not in second`: the line carries the index path, and a
    # pytest temporary directory numbered 115 puts "-1" in it, so the check
    # failed on the run counter rather than on anything the code did. Assert
    # against the reported numbers themselves.
    assert re.search(r"-\d+ (records written|notes)", second) is None
