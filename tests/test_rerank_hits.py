"""A reranker reorders fused candidates and never changes the set."""

from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.context.rerank_hits import rerank_hits
from atrium.context.retrieve_context import retrieve_context
from atrium.retrieve.hit import Hit


def _hit(record_id, text):
    return Hit(record_id, text, 1.0, "fused", "c", "a" * 64, None, "p", "assistant")


class _ByLength:
    def score(self, query, texts, deadline):
        return [float(len(text)) for text in texts]


class _Late:
    def score(self, query, texts, deadline):
        raise TimeoutError("rerank deadline passed")


class _Low:
    def score(self, query, texts, deadline):
        return [-5.0 for _ in texts]


class _Short:
    def score(self, query, texts, deadline):
        return [1.0]


_HITS = [_hit("a", "x"), _hit("b", "xxx"), _hit("c", "yyy"), _hit("d", "xx")]


def test_higher_score_first_and_ties_keep_the_fused_order():
    hits, applied = rerank_hits(_ByLength(), "q", _HITS, 1.0)
    assert [hit.record_id for hit in hits] == ["b", "c", "d", "a"]
    assert applied


def test_a_late_reranker_leaves_the_fused_order():
    assert rerank_hits(_Late(), "q", _HITS, 1.0) == (_HITS, False)


def test_a_score_count_mismatch_leaves_the_fused_order():
    assert rerank_hits(_Short(), "q", _HITS, 1.0) == (_HITS, False)


def test_context_reports_the_rerank_step_and_its_fallback(corpus):
    connection, project, state, _ = corpus
    applied = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state,
        reranker=_ByLength(),
    )  # fmt: skip
    assert applied["steps"][-1]["pass"] == "rerank"
    assert applied["steps"][-1]["applied"] is True
    assert "rerank_unavailable_fused_order" not in applied["warnings"]
    late = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state,
        reranker=_Late(),
    )  # fmt: skip
    plain = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state
    )
    assert late["steps"][-1]["applied"] is False
    assert "rerank_unavailable_fused_order" in late["warnings"]
    assert [item["record_id"] for item in late["evidence"]] == [
        item["record_id"] for item in plain["evidence"]
    ]


def test_each_reordered_hit_carries_its_cross_encoder_score():
    hits, _ = rerank_hits(_ByLength(), "q", _HITS, 1.0)
    assert [(hit.score, hit.lane) for hit in hits][:2] == [(3.0, "reranked"), (3.0, "reranked")]


def test_a_lone_candidate_is_scored_so_the_floor_can_judge_it():
    hits, applied = rerank_hits(_Low(), "q", _HITS[:1], 1.0)
    assert [(hit.record_id, hit.score, hit.lane) for hit in hits] == [("a", -5.0, "reranked")]
    assert applied
