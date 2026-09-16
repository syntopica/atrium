"""Fixture-based shared context contract checks."""

import pytest
from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.context.retrieve_context import retrieve_context
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def test_model_failure_degrades_explicitly_to_lexical(corpus):
    import numpy as np

    connection, project, state, _ = corpus

    class BrokenEmbedder:
        def embed(self, texts):
            raise OSError("model unavailable")

    with connection:
        connection.execute(
            "INSERT INTO vectors VALUES (?, ?)",
            ("history", np.array([1.0, 0.0], dtype=np.float32).tobytes()),
        )
    result = retrieve_context(
        connection, "Server-a", project=project, lane="auto", state=state, embedder=BrokenEmbedder()
    )
    assert result["evidence"]
    assert result["degraded"]
    assert "semantic_unavailable_lexical_fallback" in result["warnings"]
    assert result["route"]["history_lane"] == "words"


def test_read_only_retrieval_does_not_modify_store(corpus):
    connection, project, state, index = corpus
    before = connection.total_changes
    reader = open_store(index, read_only=True)
    result = retrieve_context(reader, "Server-a", project=project, lane="words", state=state)
    assert result["evidence"]
    assert reader.total_changes == 0
    assert connection.total_changes == before
    reader.close()


def test_missing_index_returns_structured_failure_and_creates_nothing(tmp_path):
    from atrium.context.context_from_index import context_from_index

    missing = tmp_path / "missing.sqlite3"
    result = context_from_index(missing, "Server-a", lane="words", state=tmp_path)
    assert result["index_status"] == "unavailable"
    assert result["degraded"]
    assert not missing.exists()


def test_malformed_instance_configuration_is_visible(tmp_path, monkeypatch):
    from atrium.context.context_from_index import context_from_index

    monkeypatch.delenv("ATRIUM_STATE", raising=False)
    monkeypatch.setenv("SYNTOPICA_DATA", str(tmp_path))
    (tmp_path / "syntopica.config.json").write_text("{broken")
    state = tmp_path / "atrium"
    result = context_from_index(state / "index.sqlite3", "Server-a", lane="words", state=state)
    assert result["configuration"]["status"] == "invalid"
    assert "configuration_invalid" in result["warnings"]


def test_legacy_mcp_origin_is_preserved():
    pytest.importorskip("mcp")
    from atrium.adapters.mcp_server import _rendered
    from atrium.retrieve.hit import Hit

    hits = [
        Hit(role, role, 1.0, "words", "conversation", "hash", None, "fixture", role)
        for role in ("source", "note", "synthesis", "user", "assistant", "")
    ]
    result = _rendered(hits)
    assert [row["role"] for row in result] == [hit.role for hit in hits]
    assert [row["trust"] for row in result] == [
        "untrusted",
        "curated",
        "synthesized",
        "history",
        "history",
        "unknown",
    ]


def test_third_party_records_cannot_starve_scoped_history(corpus):
    connection, project, state, _ = corpus
    with connection:
        for number in range(80):
            name = f"source-{number}"
            write_conversation(
                connection,
                name,
                [
                    Record(
                        name,
                        name,
                        name,
                        "sourcehash",
                        "fixture",
                        "source",
                        "Server-a mail routing",
                        None,
                        str(project),
                        None,
                        0,
                    )
                ],
            )
    result = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state
    )
    assert any(item["via"] == "history" for item in result["evidence"])
    assert all(item["role"] != "source" for item in result["evidence"])


def test_lexical_plan_constrains_fts_rowids_before_reading_bodies(corpus):
    from atrium.context.lexical_hits import lexical_hits

    connection, project, _, _ = corpus
    statements = []
    connection.set_trace_callback(statements.append)
    hits = lexical_hits(connection, "Server-a", 8, "words", curated=False, workspace=str(project))
    connection.set_trace_callback(None)
    assert hits
    query = next(statement for statement in statements if "WITH eligible" in statement)
    plan = connection.execute("EXPLAIN QUERY PLAN " + query).fetchall()
    assert any("MATERIALIZE eligible" in row[3] for row in plan)
    # The scope reaches the FTS table as a join, never as `rowid IN (...)`.
    # FTS5 answers a rowid-equality constraint by re-running the match query per
    # candidate rowid, and the plan says so with `VIRTUAL TABLE INDEX 0:=M1`
    # rather than `0:M1`: measured 13.57s against 0.04s for the same curated
    # query on a 1,414,461-record index (2026-09-16).
    assert not any("VIRTUAL TABLE INDEX 0:=" in row[3] for row in plan)
    assert any("SCAN e" in row[3] or "SEARCH e" in row[3] for row in plan)


def test_broad_terms_do_not_fetch_irrelevant_record_bodies(corpus):
    from atrium.context.lexical_hits import lexical_hits

    connection, project, _, _ = corpus
    with connection:
        for number in range(2000):
            name = f"broad-{number}"
            write_conversation(
                connection,
                name,
                [
                    Record(
                        name,
                        name,
                        name,
                        "broad",
                        "fixture",
                        "source",
                        "mail " * 100,
                        None,
                        str(project),
                        None,
                        0,
                    )
                ],
            )
    hits = lexical_hits(connection, "mail", 8, "words", curated=False, workspace=str(project))
    assert {hit.record_id for hit in hits} == {"history", "duplicate"}
