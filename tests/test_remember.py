"""A remembered statement is kept, indexed at once, idempotent, and supersedes on purpose."""

import json

import numpy as np
import pytest
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.context.demote_superseded import demote_superseded
from atrium.context.read_supersessions import read_supersessions
from atrium.context.supersession import Supersession
from atrium.ingest.record_identity import record_identity
from atrium.ingest.supersession_rows import supersession_rows
from atrium.remember.remember import remember
from atrium.retrieve.hit import Hit
from atrium.sql.load_sql import load_sql
from atrium.store.open_store import open_store
from atrium.synthesize.write_record import write_record

WORKSPACE = "[HOME]/p/proj"
EPISODE = {
    "job_key": "k" * 32,
    "conversation_id": "c" * 64,
    "episode_id": "e" * 24,
    "event_ids": [],
    "event_id_schema": 2,
    "segmentation": "session-self-v1",
    "model_requested": "session-claude",
    "authored_at": "2026-09-16T11:05:00.000Z",
    "workspace": WORKSPACE,
    "output": {"title": "Cache TTL", "summary": "TTL is 60s", "facts": [], "open_ends": []},
}
STATEMENT = {"title": "Cache TTL changed", "summary": "TTL is now 300s, set in cache.py"}


class _Unit:
    """A deterministic stand-in for the embedder: one unit vector per text."""

    def embed(self, texts):
        vectors = np.ones((len(texts), 384), dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _indexed_episode(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    write_record(state / "synthesis", EPISODE["job_key"], EPISODE)
    (state / "synthesis" / "active-recipe.json").write_text(json.dumps({"model_priority": []}))
    assert main(["ingest-synthesis"]) == 0
    connection = open_store(state / "index.sqlite3")
    try:
        (episode_id,) = connection.execute(load_test_sql("remember/first_synthesis_id")).fetchone()
    finally:
        connection.close()
    return state, episode_id


def _remember(state, supersedes=()):
    return remember(
        STATEMENT,
        WORKSPACE,
        supersedes=list(supersedes),
        registry=state / "synthesis",
        index=state / "index.sqlite3",
        embedder=_Unit(),
    )


def test_a_statement_is_searchable_at_once_with_its_vector(tmp_path, monkeypatch):
    state, _ = _indexed_episode(tmp_path, monkeypatch)
    receipt = _remember(state)
    assert receipt["searchable_now"] and not receipt["existed"]
    connection = open_store(state / "index.sqlite3")
    try:
        row = connection.execute(
            load_test_sql("remember/record_with_vector"), (receipt["record_id"],)
        ).fetchone()
    finally:
        connection.close()
    assert row == ("Cache TTL changed\nTTL is now 300s, set in cache.py", WORKSPACE, 1)


def test_the_next_ingest_finds_it_unchanged_and_keeps_its_vector(tmp_path, monkeypatch, capsys):
    state, _ = _indexed_episode(tmp_path, monkeypatch)
    receipt = _remember(state)
    capsys.readouterr()
    assert main(["ingest-synthesis"]) == 0
    assert "2 unchanged" in capsys.readouterr().out
    connection = open_store(state / "index.sqlite3")
    try:
        assert connection.execute(
            load_test_sql("remember/vector_count"), (receipt["record_id"],)
        ).fetchone() == (1,)
    finally:
        connection.close()


def test_repeating_a_statement_names_the_same_record(tmp_path, monkeypatch):
    state, _ = _indexed_episode(tmp_path, monkeypatch)
    first = _remember(state)
    second = _remember(state)
    assert second["existed"] and second["record_id"] == first["record_id"]


def test_a_target_the_index_does_not_hold_is_refused_before_any_write(tmp_path, monkeypatch):
    state, _ = _indexed_episode(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="not a synthesized episode"):
        _remember(state, ["f" * 64])
    assert len(list((state / "synthesis" / "records").rglob("*.json"))) == 1


def test_a_superseded_episode_is_marked_and_survives_the_next_ingest(tmp_path, monkeypatch):
    state, episode_id = _indexed_episode(tmp_path, monkeypatch)
    receipt = _remember(state, [episode_id])
    assert main(["ingest-synthesis"]) == 0
    connection = open_store(state / "index.sqlite3")
    try:
        marks = read_supersessions(connection, [episode_id, receipt["record_id"]])
    finally:
        connection.close()
    assert list(marks) == [episode_id]
    assert marks[episode_id].superseded_by == receipt["record_id"]


def test_superseded_candidates_go_last_and_nothing_is_dropped():
    def hit(record_id):
        return (Hit(record_id, "t", 1.0, "fused", "c", "s", None, "synthesis"), "history", None)

    candidates = [hit("old"), hit("new"), hit("other")]
    ordered = demote_superseded(candidates, {"old": Supersession("new", None)})
    assert [one[0].record_id for one in ordered] == ["new", "other", "old"]


def test_a_retried_older_statement_never_undoes_a_newer_supersession(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    insert = load_sql("store/insert_supersession")
    with connection:
        connection.execute(insert, ("x", "b", "2026-10-15T10:00:00Z"))
        connection.execute(insert, ("x", "a", "2026-10-15T09:00:00Z"))
    newer = connection.execute(load_test_sql("remember/supersession_of"), ("x",)).fetchone()
    with connection:
        connection.execute(insert, ("x", "c", "2026-10-15T11:00:00Z"))
    latest = connection.execute(load_test_sql("remember/supersession_of"), ("x",)).fetchone()
    connection.close()
    assert newer == ("b", "2026-10-15T10:00:00Z")
    assert latest == ("c", "2026-10-15T11:00:00Z")


def test_ingest_breaks_a_same_instant_tie_as_the_insert_does():
    at = "2026-10-15T10:00:00Z"
    records = [
        {"conversation_id": conversation, "episode_id": "e", "authored_at": at, "supersedes": ["x"]}
        for conversation in ("one", "two")
    ]
    ((_, forward, _),) = supersession_rows(records)
    ((_, backward, _),) = supersession_rows(list(reversed(records)))
    assert (
        forward
        == backward
        == max(record_identity(f"synthesis/{conversation}", "e") for conversation in ("one", "two"))
    )
