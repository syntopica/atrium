"""Both candidate populations use one atomic fallback contract."""

from unittest.mock import Mock

import pytest

from atrium.context.ordered_candidates import ordered_candidates
from atrium.context.rerank_populations import rerank_populations
from atrium.retrieve.hit import Hit


@pytest.mark.parametrize("failure", ["history", "notes", "both", None])
def test_reranking_is_atomic_across_populations(failure):
    history, notes = (
        [
            Hit(
                f"{prefix}-{index}",
                "synthetic",
                2.0 - index,
                "fused",
                "c",
                "a" * 64,
                None,
                "fixture",
                "assistant",
            )
            for index in range(2)
        ]
        for prefix in ("history", "notes")
    )
    reranker = Mock()
    reranker.score.side_effect = [
        TimeoutError("synthetic timeout") if failure in ("history", "both") else [0.0, 1.0],
        TimeoutError("synthetic timeout") if failure in ("notes", "both") else [0.0, 1.0],
    ]
    actual_history, actual_notes, step = rerank_populations(
        reranker,
        "synthetic query",
        (history, notes),
        depth=2,
    )
    assert step["applied"] is (failure is None)
    assert step["candidates"] == step["candidate_limit"] == 4
    if failure is not None:
        assert actual_history is history
        assert actual_notes is notes
        assert ordered_candidates(actual_history, actual_notes, [], step) == ordered_candidates(
            history,
            notes,
            [],
            None,
        )
    else:
        assert [hit.record_id for hit in actual_history] == ["history-1", "history-0"]
        assert [hit.record_id for hit in actual_notes] == ["notes-1", "notes-0"]
        assert all(hit.lane == "reranked" for hit in actual_history + actual_notes)
    assert [hit.record_id for hit in history] == ["history-0", "history-1"]
    assert [hit.record_id for hit in notes] == ["notes-0", "notes-1"]
    assert all(hit.lane == "fused" and hit.score in (1.0, 2.0) for hit in history + notes)
