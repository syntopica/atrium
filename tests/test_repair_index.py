"""repair-index finds a full-text index that disagrees with its records and rebuilds it."""

import json
import sqlite3

import pytest
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.store.open_store import open_store


def _archive(path):
    conversation = {
        "id": "c1",
        "source": "test",
        "provenance": {"contentSha256": "sha-c1"},
        "events": [
            {"id": "e1", "kind": "message", "role": "user", "text": "una solucion estable",
             "timestamp": "2026-10-01T00:00:00Z"}
        ],
    }  # fmt: skip
    path.write_text(
        json.dumps({"kind": "rocket-agents-conversation-export"}) + "\n" + json.dumps(conversation)
    )


@pytest.fixture
def broken(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    archive = tmp_path / "archive.jsonl"
    _archive(archive)
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", str(archive)])
    connection = open_store(index)
    with connection:
        # A delete whose text differs from what was indexed drops the row's
        # docsize but leaves its postings: the shape found in the live index on
        # 2026-10-15, a posting for a row neither records nor docsize holds.
        connection.executescript(load_test_sql("repair_index/orphan_posting"))
    connection.close()
    return index


def _ranked(index):
    connection = open_store(index, read_only=True)
    try:
        return connection.execute(load_test_sql("repair_index/ranked_estable")).fetchall()
    finally:
        connection.close()


def test_the_check_reports_the_orphan_and_changes_nothing(broken, capsys):
    with pytest.raises(sqlite3.DatabaseError):
        _ranked(broken)
    assert main(["--index", str(broken), "repair-index"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["words"]["error"] and report["substrings"]["error"] is None
    assert report["applied"] is False
    with pytest.raises(sqlite3.DatabaseError):
        _ranked(broken)


def test_apply_rebuilds_the_failing_index_and_ranked_queries_work_again(broken, capsys):
    assert main(["--index", str(broken), "repair-index", "--apply"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["words"]["error"] is None and report["words"]["rebuilt"]
    assert len(_ranked(broken)) == 1
