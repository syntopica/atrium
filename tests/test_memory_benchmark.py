"""Protect common-corpus parity and the scoring protocol from benchmark leakage."""

import json

import numpy as np
import pytest

from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation
from atrium.store.write_vectors import write_vectors
from benchmarks.memory_compare.block_network import block_network
from benchmarks.memory_compare.paired_differences import paired_differences
from benchmarks.memory_compare.prepare_snapshot import prepare_snapshot
from benchmarks.memory_compare.score_query import score_query
from benchmarks.memory_compare.summarize import summarize


def test_scoring_uses_alternatives_but_not_partial_answers():
    row = {
        "id": "q1",
        "split": "holdout",
        "strata": ["es"],
        "answer_conversation_id": "correct",
        "also_answers": ["alternative"],
        "partial": ["partial"],
    }
    result = score_query(
        row, ["synthesis/partial", "partial", "synthesis/alternative"], {"correct"}
    )
    assert result["rank"] == 2
    assert result["answerable"] is True
    assert score_query(row, ["partial"], set())["rank"] is None


def test_scoring_never_looks_beyond_eight_records():
    row = {"id": "q1", "split": "holdout", "strata": [], "answer_conversation_id": "correct"}
    assert score_query(row, ["duplicate"] * 8 + ["correct"], {"correct"})["rank"] is None


def test_errors_and_unanswerable_questions_stay_in_the_report():
    common = {"split": "holdout", "elapsed_ms": 10}
    report = summarize(
        [
            {**common, "rank": 1, "answerable": True},
            {**common, "rank": None, "answerable": False, "error": "failed"},
        ]
    )
    assert report["holdout/all"]["recall_at_8"] == 0.5
    assert report["holdout/all"]["errors"] == 1
    assert report["holdout/answerable"]["recall_at_8"] == 1


def test_snapshot_excludes_raw_and_third_party_content_and_never_changes_source(tmp_path):
    source = tmp_path / "source.sqlite3"
    connection = open_store(source)
    layout = [("a", "note"), ("b", "synthesis"), ("c", "source"), ("d", "assistant"), ("e", "note")]
    for key, role in layout:
        text = "api_key: example-placeholder" if key == "e" else "identical text"
        record = Record(key, key, key, "revision", "fixture", role, text, None, None, None, 0)
        write_conversation(connection, key, [record])
    vector = np.zeros((len(layout), 384), dtype=np.float32)
    vector[:, 0] = 1
    write_vectors(connection, [(key, "revision") for key, _ in layout], vector)
    connection.commit()
    connection.close()
    before = source.read_bytes()
    directory = tmp_path / "snapshot"
    result = prepare_snapshot(source, directory)
    assert result["records"] == 2
    assert result["excluded_by_redactor"] == 1
    corpus = [json.loads(line) for line in (directory / "corpus.jsonl").read_text().splitlines()]
    assert {row["role"] for row in corpus} == {"note", "synthesis"}
    assert source.read_bytes() == before
    with pytest.raises(FileExistsError):
        prepare_snapshot(source, directory)


def test_network_policy_rejects_connections_and_datagrams():
    for event in ("socket.connect", "socket.sendto", "socket.getaddrinfo"):
        with pytest.raises(PermissionError):
            block_network(event, ())
    block_network("open", ())


def test_paired_statistics_require_matching_questions_and_preserve_direction():
    rows = [{"split": split, "id": "q1", "rank": 1} for split in ("acceptance", "holdout")]
    missed = [{**row, "rank": None} for row in rows]
    differences = paired_differences({"atrium_reranked": rows, "other": missed})
    assert differences["holdout/atrium_reranked-minus-other"]["recall_delta"] == 1
    assert differences["holdout/atrium_reranked-minus-other"]["bootstrap_95_percent"] == [1, 1]
    with pytest.raises(ValueError):
        paired_differences({"atrium_reranked": rows, "other": []})
