"""Fixture-based shared context contract checks."""

import json
import sqlite3

import pytest
from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.context.retrieve_context import retrieve_context
from atrium.ingest.to_note_records import to_note_records
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def test_scoped_history_curated_note_and_one_hop(corpus):
    connection, project, state, _ = corpus
    result = retrieve_context(
        connection, "Nova mail routing", project=project, lane="words", state=state
    )
    evidence = result["evidence"]
    assert {item["role"] for item in evidence} == {"note", "assistant"}
    assert {item["note_path"] for item in evidence if item["role"] == "note"} == {
        "projects/nova/access.md",
        "projects/nova/runbook.md",
    }
    assert len(evidence) == 3
    assert all(item["record_id"] not in {"other", "injection"} for item in evidence)
    assert result["requires_live_verification"] is True
    assert result["freshness"]["status"] == "fresh"
    assert result["deduplicated"] == 1
    assert all(item["source_sha256"] and item["trust"] for item in evidence)
    assert all(item["date_status"] == "unknown" for item in evidence if item["role"] == "note")
    assert result["steps"][1]["scope"] == "curated_notes_in_selected_index"


def test_notes_are_not_starved_by_global_top_n(corpus):
    connection, project, state, _ = corpus
    with connection:
        for number in range(250):
            name = f"noise-{number}"
            write_conversation(
                connection,
                name,
                [
                    Record(
                        name,
                        name,
                        name,
                        "a",
                        "fixture",
                        "user",
                        "Nova mail routing",
                        "/unknown",
                        "/other",
                        None,
                        0,
                    )
                ],
            )
    result = retrieve_context(
        connection, "Nova mail routing", project=project, lane="words", state=state
    )
    assert any(item["note_path"] == "projects/nova/access.md" for item in result["evidence"])


@pytest.mark.parametrize(
    "options",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": 51},
        {"limit": True},
        {"max_chars": 0},
        {"max_chars": 100001},
        {"max_chars": 1.2},
        {"lane": "bad"},
    ],
)
def test_invalid_bounds(corpus, options):
    with pytest.raises(ValueError):
        retrieve_context(corpus[0], "Nova", lane=options.pop("lane", "words"), **options)


def test_budget_and_match_centered_excerpt(corpus):
    connection, project, state, _ = corpus
    text = "prefix " * 1000 + "unique-ñandú-42 mail receipt" + " suffix" * 1000
    with connection:
        write_conversation(
            connection,
            "long",
            [
                Record(
                    "long",
                    "long",
                    "long",
                    "hash",
                    "fixture",
                    "user",
                    text,
                    None,
                    str(project),
                    None,
                    0,
                )
            ],
        )
    result = retrieve_context(
        connection, "unique-ñandú-42", project=project, lane="words", max_chars=80, state=state
    )
    assert result["text_chars"] <= 80
    assert "unique-ñandú-42" in result["evidence"][0]["text"]
    assert result["evidence"][0]["truncated"]
    limited = retrieve_context(
        connection, "Nova", project=project, lane="words", limit=1, max_chars=1, state=state
    )
    assert len(limited["evidence"]) == 1
    assert limited["text_chars"] == 1
    json.dumps(limited, allow_nan=False)


@pytest.mark.parametrize(
    "stamp,status", [(None, "unknown"), ("bad", "invalid"), ("NaN", "invalid"), ("0", "stale")]
)
def test_missing_invalid_and_stale_refresh(corpus, stamp, status):
    connection, project, state, _ = corpus
    if stamp is None:
        (state / "last-refresh").unlink()
    else:
        (state / "last-refresh").write_text(stamp)
    result = retrieve_context(connection, "Nova", project=project, lane="words", state=state)
    assert result["freshness"]["status"] == status
    assert result["degraded"]
    assert result["warnings"]


def test_empty_and_broken_stores_are_explicit(tmp_path):
    connection = open_store(tmp_path / "empty.sqlite3")
    result = retrieve_context(connection, "Nova", lane="words", state=tmp_path)
    assert result["evidence"] == []
    assert result["index_status"] == "empty"
    assert result["degraded"]
    connection.close()
    broken = sqlite3.connect(":memory:")
    result = retrieve_context(broken, "Nova", lane="words", state=tmp_path)
    assert result["index_status"] == "unavailable"
    assert result["degraded"]
    broken.close()


def test_unmatched_query_does_not_claim_empty_store(corpus):
    result = retrieve_context(corpus[0], "nonexistent-token-998", lane="words", state=corpus[2])
    assert result["index_status"] == "ready"
    assert result["evidence"] == []
    assert "no_matches" in result["warnings"]


def test_outside_repository_does_not_widen_scope(corpus, tmp_path):
    with pytest.raises(ValueError, match="repository"):
        retrieve_context(corpus[0], "Nova", project=tmp_path, lane="words")


def test_unsafe_links_cycles_and_third_party_targets(corpus):
    connection, project, state, _ = corpus
    path = "safe.md"
    text = "Nova unsafe links [[../../outside]] [[/etc/passwd]] [[https://evil.invalid/a]] [[source]] [[safe]] [valid](projects/nova/runbook.md)"
    with connection:
        write_conversation(
            connection, path, to_note_records({"path": path, "text": text, "sha256": "safehash"})
        )
        write_conversation(
            connection,
            "source.md",
            to_note_records(
                {"path": "source.md", "text": "unsafe third party target", "sha256": "sourcehash"},
                role="source",
            ),
        )
    result = retrieve_context(
        connection, "Nova unsafe links", project=project, lane="words", state=state
    )
    assert "unsafe_link_ignored" in result["warnings"]
    assert "unresolved_indexed_link" in result["warnings"]
    assert not any(item["role"] == "source" for item in result["evidence"])
    assert len({item["record_id"] for item in result["evidence"]}) == len(result["evidence"])
    assert any(item["note_path"] == "projects/nova/runbook.md" for item in result["evidence"])
    assert not any(
        item["note_path"] == "projects/nova/second-hop.md" for item in result["evidence"]
    )


@pytest.mark.parametrize("lane", ["auto", "dense"])
def test_semantic_notes_survive_no_word_overlap_and_unrelated_history(corpus, lane):
    import numpy as np

    connection, project, state, _ = corpus

    class FakeEmbedder:
        def embed(self, texts):
            return np.array([[1.0, 0.0]], dtype=np.float32)

    with connection:
        rows = connection.execute(
            "SELECT record_id FROM records WHERE conversation_id = 'projects/nova/access.md'"
        ).fetchall()
        connection.executemany(
            "INSERT INTO vectors VALUES (?, ?)",
            [(row[0], np.array([1.0, 0.0], dtype=np.float32).tobytes()) for row in rows],
        )
        connection.execute(
            "INSERT INTO vectors VALUES (?, ?)",
            ("other", np.array([1.0, 0.0], dtype=np.float32).tobytes()),
        )
    result = retrieve_context(
        connection,
        "credenciales operativas",
        project=project,
        lane=lane,
        state=state,
        embedder=FakeEmbedder(),
    )
    assert any(item["note_path"] == "projects/nova/access.md" for item in result["evidence"])
    assert all(item["record_id"] != "other" for item in result["evidence"])
    assert result["route"]["curated_lane"] == lane
