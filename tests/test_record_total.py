"""The cached total follows all record writes and remains optional for old readers."""

import sqlite3

from load_test_sql import load_test_sql

from atrium.doctor.record_total_coherence import record_total_coherence
from atrium.record import Record
from atrium.sql.load_sql import load_sql
from atrium.store.open_store import open_store
from atrium.store.read_record_total import read_record_total
from atrium.store.write_conversation import write_conversation


def _record(record_id: str, text: str = "a useful message") -> Record:
    return Record(
        record_id=record_id,
        event_id=record_id,
        conversation_id="conv",
        source_sha256="a" * 64,
        provider="codex",
        role="user",
        text=text,
        authored_at=None,
        workspace=None,
        title=None,
        event_index=0,
    )


def test_counter_tracks_insert_update_replace_and_delete(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    assert read_record_total(connection) == 0
    with connection:
        write_conversation(connection, "conv", [_record("a"), _record("b")])
    assert read_record_total(connection) == 2
    with connection:
        write_conversation(connection, "conv", [_record("a", "changed"), _record("b")])
    assert read_record_total(connection) == 2
    with connection:
        write_conversation(connection, "conv", [_record("a")])
    assert read_record_total(connection) == 1
    with connection:
        write_conversation(connection, "conv", [])
    assert record_total_coherence(connection).severity == "ok"
    assert read_record_total(connection) == 0
    connection.close()


def test_old_read_only_index_falls_back_to_count(tmp_path):
    path = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(load_sql("store/schema"))
    connection.close()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    assert read_record_total(connection) == 0
    assert record_total_coherence(connection).severity == "warn"
    connection.close()


def test_doctor_rejects_counter_mismatch(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(connection, "conv", [_record("a")])
        connection.execute(load_test_sql("set_record_total_zero"))
    assert record_total_coherence(connection).severity == "broken"
    connection.close()
