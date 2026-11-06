"""Bookkeeping warnings are reported without calling retrieval degraded."""

from atrium.context.finalize_context import finalize_context


def _response(warnings: list[str], *, candidates: int = 3) -> dict:
    return {
        "steps": [{"pass": "words", "candidates": candidates, "candidate_limit": 64}],
        "index_status": "ready",
        "evidence": [{"record_id": "r1"}],
        "warnings": warnings,
    }


def test_a_full_candidate_pool_is_truncated_not_degraded():
    result = finalize_context(_response([], candidates=64))
    assert result["truncated"] is True
    assert "retrieval_candidate_limit_reached" in result["warnings"]
    assert result["degraded"] is False


def test_an_unresolved_note_link_is_reported_not_degraded():
    result = finalize_context(_response(["unresolved_indexed_link"]))
    assert result["warnings"] == ["unresolved_indexed_link"]
    assert result["degraded"] is False


def test_a_real_failure_beside_routine_warnings_still_degrades():
    result = finalize_context(
        _response(["unresolved_indexed_link", "rerank_unavailable_fused_order"])
    )
    assert result["degraded"] is True


def test_the_plugin_and_the_engine_agree_on_what_is_routine():
    import re
    from pathlib import Path

    from atrium.context.routine_warnings import ROUTINE_WARNINGS

    source = Path(__file__).parents[1] / "plugins/atrium-context/hooks/degradation.js"
    block = re.search(r"const ROUTINE = \[(.*?)\]", source.read_text(), re.DOTALL)
    assert block is not None
    assert set(re.findall(r"'([a-z_]+)'", block.group(1))) == ROUTINE_WARNINGS
