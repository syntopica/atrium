"""The refresh job publishes counts and instants, and nothing else writes them."""

import json
import os
import time

from atrium.cli import main
from atrium.record import Record
from atrium.status.refresh_status import refresh_status
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

SENTINEL = "the sentinel body that must never be published"


def _record(record_id, provider, event_id, authored_at):
    return Record(
        record_id=record_id,
        event_id=event_id,
        conversation_id=f"conv-{provider}",
        source_sha256="a" * 64,
        provider=provider,
        role="user",
        text=SENTINEL,
        authored_at=authored_at,
        workspace=None,
        title=None,
        event_index=0,
    )


def _index(tmp_path):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        write_conversation(
            connection,
            "conv-claude-code",
            [
                _record("r1", "claude-code", "e1", "2026-08-01T00:00:00.000Z"),
                _record("r2", "claude-code", "e2", "2026-08-02T00:00:00.000Z"),
            ],
        )
        write_conversation(connection, "conv-synthesis", [_record("s1", "synthesis", "ep-1", None)])
    connection.close()
    return path


def _registry(tmp_path):
    records = tmp_path / "registry" / "records"
    records.mkdir(parents=True)
    for position, episode in enumerate(("ep-1", "ep-2")):
        (records / f"job-{position}.json").write_text(
            json.dumps({"episode_id": episode, "model_requested": "model-a"})
        )
    (tmp_path / "registry" / "active-recipe.json").write_text(
        json.dumps({"model_priority": ["model-a"]})
    )
    return tmp_path / "registry"


def test_the_document_carries_counts_and_instants(tmp_path):
    archive = tmp_path / "archive.jsonl"
    archive.write_text("{}\n")
    os.utime(archive, (1_000_000, 1_000_000))
    stamp = tmp_path / "last-refresh"
    stamp.write_text("1000500\n")
    connection = open_store(_index(tmp_path), read_only=True)
    try:
        document = refresh_status(connection, archive, stamp, _registry(tmp_path), 1_001_000.0)
    finally:
        connection.close()
    assert document["schemaVersion"] == 1
    assert document["writtenAt"] == "1970-01-12T14:03:20Z"
    assert document["records"] == {"total": 3, "bySource": {"claude-code": 2, "synthesis": 1}}
    assert document["archive"] == {
        "at": "1970-01-12T13:46:40Z",
        "ageSeconds": 1000,
        "exists": True,
        "bytes": 3,
    }
    assert document["refresh"] == {"at": "1970-01-12T13:55:00Z", "ageSeconds": 500}
    assert document["content"]["at"] == "2026-08-02T00:00:00Z"
    assert document["populations"] == [
        {
            "model": "model-a",
            "listed": True,
            "records": 2,
            "episodes": 2,
            "intended": 2,
            "indexed": 1,
        }
    ]


def test_missing_inputs_read_as_null_not_as_fresh(tmp_path):
    connection = open_store(_index(tmp_path), read_only=True)
    try:
        document = refresh_status(
            connection, tmp_path / "absent", tmp_path / "absent", tmp_path / "absent", time.time()
        )
    finally:
        connection.close()
    assert document["archive"] == {"at": None, "ageSeconds": None, "exists": False, "bytes": None}
    assert document["refresh"] == {"at": None, "ageSeconds": None}
    assert document["populations"] == []


def _status(tmp_path, *extra):
    archive = tmp_path / "archive.jsonl"
    archive.write_text("{}\n")
    stamp = tmp_path / "last-refresh"
    stamp.write_text(str(time.time()))
    return main(
        [
            "--index",
            str(_index(tmp_path)),
            "status",
            "--archive",
            str(archive),
            "--refresh-stamp",
            str(stamp),
            "--synthesis-registry",
            str(_registry(tmp_path)),
            *extra,
        ]
    )


def test_status_publish_writes_the_file_without_content(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    assert _status(tmp_path, "--publish") == 0
    assert "records:" in capsys.readouterr().out
    published = state / "status" / "refresh.json"
    text = published.read_text()
    assert SENTINEL not in text
    assert str(tmp_path) not in text
    document = json.loads(text)
    assert document["schemaVersion"] == 1
    assert document["records"]["total"] == 3
    assert document["populations"][0]["indexed"] == 1
    assert [path.name for path in published.parent.iterdir()] == ["refresh.json"]


def test_a_plain_status_never_writes_the_file(tmp_path, monkeypatch):
    """One writer: the refresh job's `--publish`, never an operator's status."""
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    assert _status(tmp_path) == 0
    assert not (state / "status").exists()


def test_status_json_prints_the_redacted_document_and_writes_nothing(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    assert _status(tmp_path, "--json") == 0
    text = capsys.readouterr().out
    assert SENTINEL not in text
    assert str(tmp_path) not in text
    document = json.loads(text)
    assert document["schemaVersion"] == 1
    assert document["records"]["total"] == 3
    assert not (state / "status").exists()
