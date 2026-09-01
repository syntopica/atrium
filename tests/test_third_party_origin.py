"""Third-party text is marked at ingest and never travels without the mark.

A saved web article can carry an instruction, and a retrieved instruction
inside one can steer a tool-bearing agent. The origin mark is role "source":
searchable when the user asks, never embedded, never fused into semantic
answers, never injected at session start.
"""

from atrium.cli import main
from atrium.embed.semantic_roles import SEMANTIC_ROLES
from atrium.recall.recent_episodes import recent_episodes
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store


def _notes(tmp_path, name="sources"):
    root = tmp_path / name
    root.mkdir()
    (root / "article.md").write_text(
        "# Saved article\n\na third-party sentinel instruction to ignore"
    )
    return root


def test_source_is_not_a_semantic_role():
    """The security boundary: what is not semantic is never embedded."""
    assert "source" not in SEMANTIC_ROLES


def test_third_party_ingest_marks_every_record(tmp_path):
    index = tmp_path / "index.sqlite3"
    root = _notes(tmp_path)
    code = main(
        [
            "--index",
            str(index),
            "ingest-notes",
            str(root),
            "--provider",
            "brain-sources",
            "--third-party",
        ]
    )
    assert code == 0
    connection = open_store(index, read_only=True)
    rows = connection.execute("SELECT DISTINCT role, provider FROM records").fetchall()
    assert rows == [("source", "brain-sources")]
    placeholders = ",".join("?" for _ in SEMANTIC_ROLES)
    pending = connection.execute(
        f"SELECT count(*) FROM records WHERE role IN ({placeholders}) "  # noqa: S608
        "AND record_id NOT IN (SELECT record_id FROM vectors)",
        tuple(SEMANTIC_ROLES),
    ).fetchone()[0]
    connection.close()
    assert pending == 0, "third-party text must never queue for embedding"


def test_third_party_text_is_still_searchable_and_marked(tmp_path, capsys):
    index = tmp_path / "index.sqlite3"
    root = _notes(tmp_path)
    main(
        [
            "--index",
            str(index),
            "ingest-notes",
            str(root),
            "--provider",
            "brain-sources",
            "--third-party",
        ]
    )
    capsys.readouterr()
    connection = open_store(index, read_only=True)
    hits = search_words(connection, "sentinel")
    connection.close()
    assert hits and hits[0].role == "source"

    assert main(["--index", str(index), "search", "sentinel"]) == 0
    assert "UNTRUSTED THIRD-PARTY TEXT" in capsys.readouterr().out


def test_recall_never_serves_third_party_text(tmp_path):
    """Session-start injection is the attack surface the mark exists for."""
    index = tmp_path / "index.sqlite3"
    root = _notes(tmp_path)
    main(
        [
            "--index",
            str(index),
            "ingest-notes",
            str(root),
            "--provider",
            "brain-sources",
            "--third-party",
        ]
    )
    connection = open_store(index)
    with connection:
        connection.execute("UPDATE records SET workspace = '[HOME]/p/x'")
    assert recent_episodes(connection, "[HOME]/p/x", 10) == []
    connection.close()


def test_curated_notes_keep_their_first_party_role(tmp_path):
    index = tmp_path / "index.sqlite3"
    root = _notes(tmp_path, "curated")
    main(["--index", str(index), "ingest-notes", str(root)])
    connection = open_store(index, read_only=True)
    roles = connection.execute("SELECT DISTINCT role FROM records").fetchall()
    connection.close()
    assert roles == [("note",)]
