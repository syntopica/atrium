"""Status and recall must say when the memory is answering stale.

The archive sat frozen from 2026-08-27 while `status` printed healthy row
counts and the index answered every query as if current. These tests pin that
the ages print on every status, and that a session-start recall breaks its
silence when the world behind it stopped moving.
"""

import os
import time

from atrium.cli import main
from atrium.doctor.newest_content_gap import newest_content_gap
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _record(record_id, authored_at):
    return Record(
        record_id=record_id,
        event_id=f"e-{record_id}",
        conversation_id="conv",
        source_sha256="a" * 64,
        provider="claude-code",
        role="user",
        text="the sentinel body",
        authored_at=authored_at,
        workspace=None,
        title=None,
        event_index=0,
    )


def _index(tmp_path, records):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        write_conversation(connection, "conv", records)
    connection.close()
    return path


def _fresh_archive(tmp_path):
    archive = tmp_path / "archive.jsonl"
    archive.write_text("{}\n")
    return archive


def _fresh_stamp(tmp_path):
    stamp = tmp_path / "last-refresh"
    stamp.write_text(str(time.time()))
    return stamp


def test_newest_content_gap_reads_the_newest_timestamp(tmp_path):
    path = _index(tmp_path, [_record("r1", "2026-08-01T00:00:00.000Z")])
    connection = open_store(path, read_only=True)
    finding = newest_content_gap(connection)
    connection.close()
    assert finding.severity == "ok"
    assert finding.detail["newest_authored_at"] == "2026-08-01T00:00:00.000Z"
    assert isinstance(finding.detail["gap_seconds"], int)


def test_an_index_with_no_timestamps_warns_instead_of_inventing_a_gap(tmp_path):
    path = _index(tmp_path, [_record("r1", None)])
    connection = open_store(path, read_only=True)
    finding = newest_content_gap(connection)
    connection.close()
    assert finding.severity == "warn"


def test_status_says_stale_when_the_archive_stopped_moving(tmp_path, capsys):
    index = _index(tmp_path, [_record("r1", "2026-08-01T00:00:00.000Z")])
    archive = _fresh_archive(tmp_path)
    stale = time.time() - 30 * 86400
    os.utime(archive, (stale, stale))
    absent_stamp = tmp_path / "no-stamp"
    code = main(
        [
            "--index",
            str(index),
            "status",
            "--archive",
            str(archive),
            "--refresh-stamp",
            str(absent_stamp),
            "--synthesis-registry",
            str(tmp_path / "no-registry"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "BROKEN" in out
    assert "newest indexed content authored" in out


def test_status_stays_quiet_when_everything_is_fresh(tmp_path, capsys):
    index = _index(tmp_path, [_record("r1", "2026-08-01T00:00:00.000Z")])
    archive = _fresh_archive(tmp_path)
    stamp = _fresh_stamp(tmp_path)
    main(
        [
            "--index",
            str(index),
            "status",
            "--archive",
            str(archive),
            "--refresh-stamp",
            str(stamp),
            "--synthesis-registry",
            str(tmp_path / "no-registry"),
        ]
    )
    out = capsys.readouterr().out
    assert "archive last written" in out
    assert "last refresh finished" in out
    assert "BROKEN" not in out
    assert "STALE" not in out


def test_recall_breaks_its_silence_when_the_memory_is_stale(tmp_path, capsys):
    """The empty recall block is exactly the case where nothing else says so."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    index = _index(tmp_path, [_record("r1", "2026-08-01T00:00:00.000Z")])
    code = main(
        [
            "--index",
            str(index),
            "recall",
            "--cwd",
            str(repo),
            "--archive",
            str(tmp_path / "no-archive.jsonl"),
            "--refresh-stamp",
            str(tmp_path / "no-stamp"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "memory may be stale" in out


def test_recall_stays_silent_when_fresh_and_empty(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    index = _index(tmp_path, [_record("r1", "2026-08-01T00:00:00.000Z")])
    code = main(
        [
            "--index",
            str(index),
            "recall",
            "--cwd",
            str(repo),
            "--archive",
            str(_fresh_archive(tmp_path)),
            "--refresh-stamp",
            str(_fresh_stamp(tmp_path)),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert out == ""
