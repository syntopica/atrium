"""A rerank keeps whatever it scored in time and never changes the candidate set."""

import itertools

from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.context.ordered_candidates import ordered_candidates
from atrium.context.reorder_scored import reorder_scored
from atrium.context.rerank_populations import rerank_populations
from atrium.context.retrieve_context import retrieve_context
from atrium.context.score_until_deadline import score_until_deadline
from atrium.retrieve.hit import Hit


def _hit(record_id, text, score=1.0):
    return Hit(record_id, text, score, "fused", "c", "a" * 64, None, "p", "assistant")


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
        return []


class _ThenLate:
    """Answers the first ``n`` pairs, then the deadline has passed."""

    def __init__(self, n):
        self.left = itertools.count(n, -1)

    def score(self, query, texts, deadline):
        if next(self.left) <= 0:
            raise TimeoutError("rerank deadline passed")
        return [float(len(text)) for text in texts]


_HITS = [_hit("a", "x"), _hit("b", "xxx"), _hit("c", "yyy"), _hit("d", "xx")]


def test_higher_score_first_and_ties_keep_the_fused_order():
    hits = reorder_scored(_HITS, score_until_deadline(_ByLength(), "q", _HITS, 1e18))
    assert [hit.record_id for hit in hits] == ["b", "c", "d", "a"]
    assert [(hit.score, hit.lane) for hit in hits][:2] == [(3.0, "reranked"), (3.0, "reranked")]


def test_a_late_or_miscounting_reranker_scores_nothing_and_keeps_the_fused_order():
    for reranker in (_Late(), _Short()):
        scores = score_until_deadline(reranker, "q", _HITS, 1e18)
        assert scores == {}
        assert reorder_scored(_HITS, scores) == _HITS


def test_a_lone_candidate_is_scored_so_the_floor_can_judge_it():
    hits = reorder_scored(_HITS[:1], score_until_deadline(_Low(), "q", _HITS[:1], 1e18))
    assert [(hit.record_id, hit.score, hit.lane) for hit in hits] == [("a", -5.0, "reranked")]


def test_a_rerank_cut_short_keeps_the_scored_head_of_both_populations():
    history = [_hit("h0", "x"), _hit("h1", "xxxx"), _hit("h2", "xxxxx")]
    notes = [_hit("n0", "y"), _hit("n1", "yyy")]
    actual_history, actual_notes, step = rerank_populations(
        _ThenLate(4), "q", (history, notes), depth=3
    )
    assert step["applied"] is False
    assert step["scored"] == 4
    assert step["candidates"] == 5
    # h0, n0, h1, n1 were scored; h2 keeps its fused place after them.
    assert [hit.record_id for hit in actual_history] == ["h1", "h0", "h2"]
    assert [hit.record_id for hit in actual_notes] == ["n1", "n0"]
    assert [hit.lane for hit in actual_history] == ["reranked", "reranked", "fused"]
    order = [
        hit.record_id for hit, _, _ in ordered_candidates(actual_history, actual_notes, [], step)
    ]
    assert order == ["h1", "n1", "h0", "n0", "h2"]
    assert [hit.record_id for hit in history] == ["h0", "h1", "h2"]
    assert all(hit.lane == "fused" for hit in history + notes)


def test_nothing_scored_is_the_plain_alternation():
    history, notes = [_hit("h0", "x"), _hit("h1", "xx")], [_hit("n0", "y")]
    actual_history, actual_notes, step = rerank_populations(_Late(), "q", (history, notes), depth=2)
    assert step["scored"] == 0 and step["applied"] is False
    assert ordered_candidates(actual_history, actual_notes, [], step) == ordered_candidates(
        history, notes, [], None
    )


def test_context_reports_the_rerank_step_and_its_fallbacks(corpus):
    connection, project, state, _ = corpus
    applied = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state,
        reranker=_ByLength(),
    )  # fmt: skip
    assert applied["steps"][-1]["pass"] == "rerank"
    assert applied["steps"][-1]["applied"] is True
    assert not {"rerank_unavailable_fused_order", "rerank_partial_fused_tail"} & set(
        applied["warnings"]
    )
    partial = retrieve_context(
        connection, "Server-a mail routing", project=project, lane="words", state=state,
        reranker=_ThenLate(1),
    )  # fmt: skip
    assert partial["steps"][-1]["scored"] == 1
    assert "rerank_partial_fused_tail" in partial["warnings"]
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
