"""The resident dense matrix ranks exactly like the index scan it replaces."""

import numpy as np
import pytest
from load_test_sql import load_test_sql

from atrium.context.build_dense_matrix import build_dense_matrix
from atrium.context.dense_hits import dense_hits
from atrium.context.dense_matrix_hits import dense_matrix_hits
from atrium.context.load_dense_matrix import load_dense_matrix
from atrium.context.read_dense_generation import read_dense_generation
from atrium.context.save_dense_matrix import save_dense_matrix
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation
from atrium.store.write_vectors import write_vectors

_PROJECT = "/work/server-a"


def _record(record_id, role, workspace):
    return Record(
        record_id,
        record_id,
        record_id,
        "s",
        "fixture",
        role,
        f"text of {record_id}",
        "2026-10-10T00:00:00Z",
        workspace,
        None,
        0,
    )


@pytest.fixture
def store(tmp_path):
    rng = np.random.default_rng(11)
    layout = [
        ("note-1", "note", None),
        ("note-2", "note", "/elsewhere"),
        ("syn-root", "synthesis", _PROJECT),
        ("syn-child", "synthesis", _PROJECT + "/sub"),
        ("syn-sibling", "synthesis", _PROJECT + "-other"),
        ("syn-far", "synthesis", "/other"),
    ] + [(f"syn-{n}", "synthesis", _PROJECT) for n in range(20)]
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        for record_id, role, workspace in layout:
            write_conversation(connection, record_id, [_record(record_id, role, workspace)])
        vectors = rng.standard_normal((len(layout), 8)).astype(np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        write_vectors(connection, [(row[0], "s") for row in layout], vectors)
    yield connection
    connection.close()


@pytest.mark.parametrize(("curated", "workspace"), [(True, None), (False, _PROJECT), (False, None)])
def test_matrix_ranks_like_the_index_scan(store, curated, workspace):
    matrix = build_dense_matrix(store)
    query = np.linspace(-1.0, 1.0, 8).astype(np.float32)
    expected = dense_hits(store, query, 10, curated=curated, workspace=workspace)
    actual = dense_matrix_hits(store, matrix, query, 10, curated=curated, workspace=workspace)
    assert [hit.record_id for hit in actual] == [hit.record_id for hit in expected]
    assert [hit.score for hit in actual] == pytest.approx([hit.score for hit in expected])
    assert [hit.text for hit in actual] == [hit.text for hit in expected]


def test_workspace_scope_keeps_children_and_drops_siblings(store):
    matrix = build_dense_matrix(store)
    hits = dense_matrix_hits(
        store, matrix, np.ones(8, dtype=np.float32), 50, curated=False, workspace=_PROJECT
    )
    found = {hit.record_id for hit in hits}
    assert {"syn-root", "syn-child"} <= found
    assert not found & {"syn-sibling", "syn-far", "note-1", "note-2"}


def test_every_vector_change_moves_the_generation(store):
    start = read_dense_generation(store)
    with store:
        write_vectors(store, [("syn-root", "s")], np.ones((1, 8), dtype=np.float32))
    replaced = read_dense_generation(store)
    with store:
        write_conversation(store, "syn-far", [])
    assert start is not None
    assert replaced > start
    assert read_dense_generation(store) > replaced


def test_matrix_carries_the_generation_of_its_snapshot(store):
    assert build_dense_matrix(store).generation == read_dense_generation(store)


def test_a_stale_matrix_skips_deleted_records_and_still_fills_the_limit(store):
    matrix = build_dense_matrix(store)
    query = np.ones(8, dtype=np.float32)
    winner = dense_matrix_hits(store, matrix, query, 1, curated=False, workspace=_PROJECT)[0]
    with store:
        write_conversation(store, winner.record_id, [])
    hits = dense_matrix_hits(store, matrix, query, 5, curated=False, workspace=_PROJECT)
    assert len(hits) == 5
    assert winner.record_id not in {hit.record_id for hit in hits}


def test_saved_matrix_round_trips_and_refuses_damage(store, tmp_path):
    matrix = build_dense_matrix(store)
    path = tmp_path / "dense-matrix.npz"
    save_dense_matrix(matrix, path)
    loaded = load_dense_matrix(path)
    assert loaded is not None
    assert loaded.generation == matrix.generation
    assert list(loaded.ids) == list(matrix.ids)
    assert np.array_equal(loaded.vectors, matrix.vectors)
    path.write_bytes(b"not a matrix")
    assert load_dense_matrix(path) is None
    assert load_dense_matrix(tmp_path / "missing.npz") is None


def test_an_index_without_the_counter_reads_as_unversioned(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        connection.execute(load_test_sql("drop_dense_generation"))
    assert read_dense_generation(connection) is None
    connection.close()
