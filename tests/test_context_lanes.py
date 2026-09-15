"""Fixture-based shared context contract checks."""

from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.context.retrieve_context import retrieve_context
from atrium.store.open_store import open_store


def test_no_vectors_degrades_each_requested_semantic_pass(corpus):
    result = retrieve_context(corpus[0], "Server-a", project=corpus[1], lane="dense", state=corpus[2])
    assert result["route"] == {
        "requested_lane": "dense",
        "history_lane": "words",
        "curated_lane": "words",
    }
    assert "curated_vectors_missing_lexical_fallback" in result["warnings"]
    assert "history_vectors_missing_lexical_fallback" in result["warnings"]
    assert any(item["via"] == "history" for item in result["evidence"])


def test_another_index_does_not_inherit_selected_instances_freshness(corpus, tmp_path):
    from atrium.context.context_from_index import context_from_index

    _, _, state, _ = corpus
    other = tmp_path / "other.sqlite3"
    open_store(other).close()
    result = context_from_index(other, "Server-a", state=state, lane="words")
    assert result["freshness"]["status"] == "unknown"
    assert "index_state_mismatch" in result["warnings"]
