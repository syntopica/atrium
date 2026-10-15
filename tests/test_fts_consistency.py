"""The doctor's ranked probe catches a posting left for a deleted row."""

from load_test_sql import load_test_sql

from atrium.doctor.fts_consistency import fts_consistency
from atrium.ingest.to_note_records import to_note_records
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _store(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    text = "# Note\n\nThe deploy goes through the release checkout and que funciona.\n"
    with connection:
        write_conversation(
            connection,
            "brain/n.md",
            to_note_records({"path": "brain/n.md", "text": text, "sha256": "a" * 64}),
        )
    return connection


def test_a_consistent_index_passes(tmp_path):
    assert fts_consistency(_store(tmp_path)).severity == "ok"


def test_an_orphan_posting_with_a_common_word_is_broken(tmp_path):
    connection = _store(tmp_path)
    with connection:
        connection.executescript(load_test_sql("fts_consistency/orphan_common_word"))
    finding = fts_consistency(connection)
    assert finding.severity == "broken"
    assert finding.code == "fts_orphan_postings"
    assert list(finding.detail["failed"]) == ["words"]
