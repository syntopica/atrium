"""Canonical observing hosts survive indexing without rewriting text or vectors."""

import json
from dataclasses import replace

import numpy as np
import pytest
from load_test_sql import load_test_sql

from atrium.adapters.rendered_hits import rendered_hits
from atrium.commands.run_ingest import run_ingest
from atrium.context.read_dense_generation import read_dense_generation
from atrium.context.retrieve_context import retrieve_context
from atrium.ingest.to_records import to_records
from atrium.retrieve.search import search
from atrium.store.open_store import open_store
from atrium.store.read_record_hosts import read_record_hosts
from atrium.store.write_conversation import UNCHANGED, write_conversation
from atrium.store.write_vectors import write_vectors


def _conversation(hosts=None):
    conversation = {
        "id": "canonical-fixture",
        "source": "claude",
        "title": "Durable routing decision",
        "provenance": {"contentSha256": "same-text-revision"},
        "events": [
            {"id": "e1", "kind": "message", "role": "assistant", "text": "Routing uses Atlas."}
        ],
    }
    if hosts is not None:
        conversation["hosts"] = hosts
    return conversation


def test_hosts_roundtrip_reindex_preserves_vectors_and_avoids_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path / "state"))
    archive = tmp_path / "canonical.jsonl"
    index = tmp_path / "index.sqlite3"
    archive.write_text(json.dumps(_conversation(["macbook"])), encoding="utf-8")
    assert run_ingest(index, archive) == 0
    connection = open_store(index)
    (record,) = to_records(_conversation(["macbook"]))
    with connection:
        write_vectors(
            connection, [(record.record_id, record.source_sha256)], np.array([[1.0, 0.0]])
        )
    before = connection.execute(load_test_sql("hosts/vector"), (record.record_id,)).fetchone()
    connection.close()
    reader = open_store(index, read_only=True)
    first = retrieve_context(reader, "Atlas", lane="words", state=tmp_path / "state")
    assert first["evidence"][0]["hosts"] == ["macbook"]
    generation = read_dense_generation(reader)

    hosts = ['peer "quoted"\nobserver', "macbook", "macbook"]
    archive.write_text(json.dumps(_conversation(hosts)), encoding="utf-8")
    assert run_ingest(index, archive) == 0
    assert run_ingest(index, archive) == 0
    connection = reader
    try:
        assert read_dense_generation(connection) == generation
        assert (
            connection.execute(load_test_sql("hosts/vector"), (record.record_id,)).fetchone()
            == before
        )
        for lane in ("words", "substring"):
            result = rendered_hits(search(connection, "Atlas", 10, lane), connection=connection)
            assert len(result) == 1
            assert result[0]["hosts"] == sorted(set(hosts))
            assert result[0]["source_sha256"] == "same-text-revision"
        response = retrieve_context(connection, "Atlas", lane="words", state=tmp_path / "state")
        assert response["index_status"] == "ready"
        assert response["evidence"][0]["hosts"] == sorted(set(hosts))
    finally:
        connection.close()


def test_legacy_readers_stay_read_only_and_forward_migration_backfills(tmp_path):
    index = tmp_path / "index.sqlite3"
    (record,) = to_records(_conversation())
    connection = open_store(index)
    with connection:
        write_conversation(connection, record.conversation_id, [record])
        connection.execute(load_test_sql("hosts/drop_record_hosts"))
    connection.close()
    before = index.read_bytes()
    connection = open_store(index, read_only=True)
    try:
        assert read_record_hosts(connection, [record.record_id]) == {}
        results = rendered_hits(search(connection, "Atlas", 5, "words"), connection=connection)
        assert "hosts" not in results[0]
    finally:
        connection.close()
    assert index.read_bytes() == before

    connection = open_store(index)
    try:
        assert read_record_hosts(connection, [record.record_id]) == {}
        with connection:
            assert (
                write_conversation(
                    connection,
                    record.conversation_id,
                    [replace(record, hosts=("peer-a", "peer-b"))],
                )
                == UNCHANGED
            )
        assert read_record_hosts(connection, [record.record_id]) == {
            record.record_id: ["peer-a", "peer-b"]
        }
        with connection:
            write_conversation(connection, record.conversation_id, [record])
        assert read_record_hosts(connection, [record.record_id]) == {}
        with connection:
            write_conversation(
                connection, record.conversation_id, [replace(record, hosts=("peer-a",))]
            )
            write_conversation(connection, record.conversation_id, [])
        assert read_record_hosts(connection, [record.record_id]) == {}
    finally:
        connection.close()


@pytest.mark.parametrize("hosts", ["macbook", [""], [42], {}])
def test_invalid_canonical_host_labels_are_rejected(hosts):
    with pytest.raises(ValueError, match="hosts"):
        list(to_records(_conversation(hosts)))
