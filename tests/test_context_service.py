"""The resident service answers like in-process retrieval, and fails loudly."""

import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export
from load_test_sql import load_test_sql

from atrium.context.finish_margin_s import FINISH_MARGIN_S
from atrium.context.read_dense_generation import read_dense_generation
from atrium.context.retrieve_context import retrieve_context
from atrium.serve.context_server import ContextServer
from atrium.serve.deadline_reranker import DeadlineReranker
from atrium.serve.dense_matrix_holder import DenseMatrixHolder
from atrium.serve.request_context_service import request_context_service


class FakeEmbedder:
    def embed(self, texts):
        return np.array([[1.0, 0.0]], dtype=np.float32)


@pytest.fixture
def served(corpus):
    connection, project, state, index = corpus
    with connection:
        rows = connection.execute(
            load_test_sql("context/select_server_a_access_record_ids")
        ).fetchall()
        connection.executemany(
            load_test_sql("insert_vector"),
            [(row[0], np.array([1.0, 0.0], dtype=np.float32).tobytes()) for row in rows],
        )
    # AF_UNIX paths are limited to about 104 bytes; pytest's tmp_path is longer.
    short = Path(tempfile.mkdtemp(prefix="atr", dir="/tmp"))
    holder = DenseMatrixHolder(index, short / "dense-matrix.npz")
    holder.prepare()
    server = ContextServer(short / "context.sock", index, holder, FakeEmbedder())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield connection, project, state, index, short / "context.sock", holder
    server.shutdown()
    server.server_close()
    shutil.rmtree(short)


def _request(index, project, state):
    return {
        "index": str(index),
        "query": "credenciales operativas",
        "project": str(project),
        "limit": 4,
        "max_chars": 1400,
        "lane": "dense",
        "state": str(state),
    }


def test_service_answers_like_in_process_retrieval(served):
    connection, project, state, index, path, _ = served
    reply = request_context_service(path, _request(index, project, state), timeout=10)
    local = retrieve_context(
        connection,
        "credenciales operativas",
        project=project,
        limit=4,
        max_chars=1400,
        lane="dense",
        state=state,
        embedder=FakeEmbedder(),
    )
    assert [item["record_id"] for item in reply["evidence"]] == [
        item["record_id"] for item in local["evidence"]
    ]
    assert any(item["note_path"] == "projects/server-a/access.md" for item in reply["evidence"])
    assert [step["pass"] for step in reply["steps"]] == ["history", "curated", "links"]
    assert all(isinstance(step["ms"], int) and step["ms"] >= 0 for step in reply["steps"])


def test_service_refuses_another_index(served, tmp_path):
    _, project, state, _, path, _ = served
    reply = request_context_service(
        path, _request(tmp_path / "other.sqlite3", project, state), timeout=10
    )
    assert reply == {"error": "index_mismatch"}


def test_no_service_means_none(tmp_path):
    assert request_context_service(tmp_path / "absent.sock", {}, timeout=1) is None


def test_a_silent_service_times_out_instead_of_hanging():
    short = Path(tempfile.mkdtemp(prefix="atr", dir="/tmp"))
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(short / "context.sock"))
    listener.listen(1)
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            request_context_service(short / "context.sock", {"query": "x"}, timeout=0.3)
    finally:
        listener.close()
        shutil.rmtree(short)
    assert time.monotonic() - started < 2


def test_a_stale_matrix_is_reported_and_rebuilt(served):
    connection, project, state, index, path, holder = served
    with connection:
        connection.execute(
            load_test_sql("insert_vector"),
            ("history", np.array([0.0, 1.0], dtype=np.float32).tobytes()),
        )
    reply = request_context_service(path, _request(index, project, state), timeout=10)
    assert "dense_matrix_stale_rebuilding" in reply["warnings"]
    assert reply["degraded"] is True
    live = read_dense_generation(connection)
    deadline = time.monotonic() + 10
    while holder.matrix.generation != live and time.monotonic() < deadline:
        time.sleep(0.05)
    assert holder.matrix.generation == live
    reply = request_context_service(path, _request(index, project, state), timeout=10)
    assert "dense_matrix_stale_rebuilding" not in reply["warnings"]


class _NeverFinishes:
    """A reranker as slow as a loaded machine: it works until its deadline."""

    def __init__(self):
        self.deadlines = []

    def score(self, query, texts, deadline):
        self.deadlines.append(deadline)
        while time.monotonic() <= deadline:
            time.sleep(0.05)
        raise TimeoutError("rerank deadline passed")


class _Instant:
    def __init__(self):
        self.deadlines = []

    def score(self, query, texts, deadline):
        self.deadlines.append((deadline, time.monotonic()))
        return [0.0 for _ in texts]


def _serve_with(index, holder, reranker):
    short = Path(tempfile.mkdtemp(prefix="atr", dir="/tmp"))
    server = ContextServer(short / "context.sock", index, holder, FakeEmbedder(), reranker)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, short


def test_a_slow_rerank_stops_in_time_for_the_client_that_waits(served):
    _, project, state, index, _, holder = served
    reranker = _NeverFinishes()
    server, short = _serve_with(index, holder, reranker)
    request = {**_request(index, project, state), "timeout_s": 1.5}
    started = time.monotonic()
    try:
        reply = request_context_service(short / "context.sock", request, timeout=1.5)
        elapsed = time.monotonic() - started
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(short)
    # Without the client's deadline the rerank would spend its whole 3 s budget
    # and the client, waiting 1.5 s, would get nothing.
    assert elapsed < 1.5
    assert "rerank_unavailable_fused_order" in reply["warnings"]
    assert reply["evidence"]
    assert reranker.deadlines


def test_a_request_without_a_deadline_keeps_the_whole_rerank_budget(served):
    _, project, state, index, _, holder = served
    reranker = _Instant()
    server, short = _serve_with(index, holder, reranker)
    try:
        reply = request_context_service(
            short / "context.sock", _request(index, project, state), timeout=10
        )
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(short)
    assert "rerank_unavailable_fused_order" not in reply["warnings"]
    deadline, called = reranker.deadlines[0]
    assert 2.5 < deadline - called <= 3.0


def test_the_client_deadline_only_ever_shortens_the_rerank():
    inner = _Instant()
    wrapped = DeadlineReranker(inner, client_deadline=100.0)
    wrapped.score("q", ["a"], deadline=50.0)
    wrapped.score("q", ["a"], deadline=200.0)
    assert [deadline for deadline, _ in inner.deadlines] == [50.0, 100.0 - FINISH_MARGIN_S]
