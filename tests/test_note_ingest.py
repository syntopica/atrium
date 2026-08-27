"""Curated notes become records with the same convergence guarantees."""

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
