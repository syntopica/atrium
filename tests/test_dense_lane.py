"""The dense lane, its fusion, and the adaptive routing between them."""

import numpy as np

from atrium.record import Record
from atrium.retrieve.fuse_ranked import fuse_ranked
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_dense import search_dense
from atrium.retrieve.search_hybrid import search_hybrid
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation
from atrium.store.write_vectors import write_vectors


def _record(record_id, text, role="note"):
    return Record(
        record_id=record_id,
        event_id=record_id,
        conversation_id="c",
        source_sha256="s",
        provider="test",
        role=role,
        text=text,
        authored_at=None,
        workspace=None,
        title=None,
        event_index=0,
    )


def _hit(record_id, score, lane):
    return Hit(
        record_id=record_id,
        text=record_id,
        score=score,
        lane=lane,
        conversation_id="c",
        source_sha256="s",
        authored_at=None,
        provider="test",
    )


class _FakeEmbedder:
    """Deterministic stand-in so routing tests need no 300 MB model."""

    def __init__(self, vector):
        self._vector = np.asarray(vector, dtype=np.float32)

    def embed(self, texts):
        return np.tile(self._vector, (len(texts), 1))


def _store_with_vectors(tmp_path, vectors_by_id, texts_by_id=None):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(
            connection,
            "c",
            [_record(rid, (texts_by_id or {}).get(rid, rid)) for rid in vectors_by_id],
        )
        write_vectors(
            connection,
            [(rid, "s") for rid in vectors_by_id],
            np.asarray(list(vectors_by_id.values()), dtype=np.float32),
        )
    return connection


def test_dense_search_ranks_by_cosine(tmp_path):
    connection = _store_with_vectors(
        tmp_path, {"near": [1.0, 0.0], "far": [0.0, 1.0], "mid": [0.7, 0.7]}
    )
    hits = search_dense(connection, np.asarray([1.0, 0.0], dtype=np.float32), limit=2)
    connection.close()
    assert [h.record_id for h in hits] == ["near", "mid"]
    assert all(h.lane == "dense" for h in hits)


def test_deleting_a_record_deletes_its_vector(tmp_path):
    """Reconciliation must reach the dense lane: a superseded record's vector
    cannot linger and keep answering queries."""
    connection = _store_with_vectors(tmp_path, {"old": [1.0, 0.0]})
    with connection:
        write_conversation(connection, "c", [_record("new", "replacement")])
    remaining = connection.execute("SELECT record_id FROM vectors").fetchall()
    connection.close()
    assert remaining == []


def test_fusion_weights_favour_the_lexical_lane():
    """70/30 weighted RRF: with symmetric ranks, the lexical top hit wins."""
    fused = fuse_ranked([_hit("lex", 5.0, "words")], [_hit("den", 0.9, "dense")])
    assert [h.record_id for h in fused] == ["lex", "den"]
    assert all(h.lane == "fused" for h in fused)


def test_a_hit_in_both_lanes_outranks_single_lane_hits():
    fused = fuse_ranked(
        [_hit("both", 4.0, "words"), _hit("lex", 5.0, "words")],
        [_hit("both", 0.8, "dense"), _hit("den", 0.9, "dense")],
    )
    assert fused[0].record_id == "both"


def test_hybrid_routes_to_dense_alone_when_lexical_is_blind(tmp_path):
    """When no query word appears in the corpus, fusing would bury the only
    working signal (12% -> 8% R@10 measured), so dense answers alone."""
    connection = _store_with_vectors(
        tmp_path, {"a": [1.0, 0.0]}, texts_by_id={"a": "unrelated prose"}
    )
    hits = search_hybrid(connection, _FakeEmbedder([1.0, 0.0]), "zzzmissing", limit=5)
    connection.close()
    assert [h.record_id for h in hits] == ["a"]
    assert hits[0].lane == "dense"


def test_hybrid_degrades_to_lexical_when_nothing_is_embedded(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(connection, "c", [_record("a", "plain retrieval prose")])
    hits = search_hybrid(connection, _FakeEmbedder([1.0, 0.0]), "retrieval", limit=5)
    connection.close()
    assert [h.record_id for h in hits] == ["a"]
    assert hits[0].lane == "words"


def test_a_stale_revision_never_gets_its_vector_stored(tmp_path):
    """Embedding takes seconds; a reconciliation landing in between must not
    leave a vector computed from superseded text attached to the new revision."""
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        write_conversation(connection, "c", [_record("a", "new meaning")])
        written = write_vectors(
            connection, [("a", "sha-of-the-old-revision")], np.asarray([[1.0, 0.0]])
        )
    remaining = connection.execute("SELECT count(*) FROM vectors").fetchone()[0]
    connection.close()
    assert written == 0
    assert remaining == 0


def test_hybrid_fetches_deeper_than_the_requested_limit(tmp_path):
    """With limit=1, a record ranked second in BOTH lanes must still win the
    fusion -- reusing the output limit as candidate depth returned the wrong
    top result."""
    connection = _store_with_vectors(
        tmp_path,
        {"both": [0.8, 0.2], "dense-only": [1.0, 0.0]},
        texts_by_id={
            "both": "retrieval retrieval prose",
            "dense-only": "unrelated words entirely",
        },
    )
    with connection:
        write_conversation(
            connection,
            "c2",
            [
                Record(
                    record_id="lex-only",
                    event_id="lex-only",
                    conversation_id="c2",
                    source_sha256="s",
                    provider="test",
                    role="user",
                    text="retrieval retrieval retrieval retrieval",
                    authored_at=None,
                    workspace=None,
                    title=None,
                    event_index=0,
                )
            ],
        )
    hits = search_hybrid(connection, _FakeEmbedder([1.0, 0.0]), "retrieval", limit=1)
    connection.close()
    assert [h.record_id for h in hits] == ["both"]


def test_equal_scores_rank_identically_whatever_the_insertion_order(tmp_path):
    """A fresh build and a reconciled build store identical rows in different
    physical order; equal-score dense results must not follow row order."""

    def build(tmp, ids):
        connection = open_store(tmp)
        with connection:
            write_conversation(connection, "c", [_record(rid, rid) for rid in ids])
            write_vectors(
                connection, [(rid, "s") for rid in ids], np.asarray([[1.0, 0.0]] * len(ids))
            )
        return connection

    first = build(tmp_path / "one.sqlite3", ["b", "a"])
    second = build(tmp_path / "two.sqlite3", ["a", "b"])
    query = np.asarray([1.0, 0.0], dtype=np.float32)
    order_one = [h.record_id for h in search_dense(first, query)]
    order_two = [h.record_id for h in search_dense(second, query)]
    first.close()
    second.close()
    assert order_one == order_two == ["a", "b"]


def test_hybrid_fuses_when_both_lanes_see_the_query(tmp_path):
    connection = _store_with_vectors(
        tmp_path,
        {"a": [1.0, 0.0], "b": [0.0, 1.0]},
        texts_by_id={"a": "retrieval layer notes", "b": "retrieval appendix"},
    )
    hits = search_hybrid(connection, _FakeEmbedder([1.0, 0.0]), "retrieval", limit=5)
    connection.close()
    assert {h.record_id for h in hits} == {"a", "b"}
    assert all(h.lane == "fused" for h in hits)
