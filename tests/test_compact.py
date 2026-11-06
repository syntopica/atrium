"""compact reclaims the space deleted records leave in the full-text lanes."""

import json

import pytest
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.store.open_store import open_store


def _archive(path, conversations):
    rows = [json.dumps({"kind": "rocket-agents-conversation-export"})]
    for number in range(conversations):
        words = " ".join(f"palabra{number}x{index}" for index in range(400))
        rows.append(
            json.dumps(
                {
                    "id": f"c{number}",
                    "source": "test",
                    "provenance": {"contentSha256": f"sha-c{number}"},
                    "events": [
                        {
                            "id": "e1",
                            "kind": "message",
                            "role": "user",
                            "text": f"una solucion estable {words}",
                            "timestamp": "2026-10-01T00:00:00Z",
                        }
                    ],
                }
            )
        )
    path.write_text("\n".join(rows))


@pytest.fixture
def shrunk(tmp_path, monkeypatch):
    """An index that held 300 conversations and now holds one."""
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    index = state / "index.sqlite3"
    archive = tmp_path / "archive.jsonl"
    _archive(archive, 300)
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    _archive(archive, 1)
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    connection = open_store(index)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()
    return index


def _ranked(index, name):
    connection = open_store(index, read_only=True)
    try:
        return connection.execute(load_test_sql(f"compact/{name}")).fetchall()
    finally:
        connection.close()


def test_without_apply_only_the_size_is_reported(shrunk, capsys):
    before = shrunk.stat().st_size
    assert main(["--index", str(shrunk), "compact"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {"applied": False, "bytes_before": before}
    assert shrunk.stat().st_size == before


def test_apply_shrinks_the_file_and_both_lanes_still_answer(shrunk, capsys):
    before = shrunk.stat().st_size
    words, substrings = _ranked(shrunk, "ranked_words"), _ranked(shrunk, "ranked_substrings")
    assert main(["--index", str(shrunk), "compact", "--apply"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["applied"] is True
    assert report["bytes_after"] < before / 4
    assert shrunk.stat().st_size == report["bytes_after"]
    assert _ranked(shrunk, "ranked_words") == words and len(words) == 1
    assert _ranked(shrunk, "ranked_substrings") == substrings and len(substrings) == 1
    assert main(["--index", str(shrunk), "repair-index"]) == 0


def test_a_running_refresh_refuses_it(shrunk, capsys):
    import fcntl

    with (shrunk.parent / "refresh.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        assert main(["--index", str(shrunk), "compact", "--apply"]) == 3
    assert "refused" in capsys.readouterr().out
