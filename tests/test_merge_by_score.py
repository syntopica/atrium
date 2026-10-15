"""Reranked history and notes share one order by logit; weak candidates are not evidence."""

from atrium.context.merge_by_score import merge_by_score
from atrium.retrieve.hit import Hit


def _hit(record_id, score, role="synthesis"):
    return Hit(record_id, record_id, score, "reranked", "c", "s", None, "p", role)


def test_a_strong_note_outranks_weak_history_and_brings_its_links():
    history = [_hit("h1", 0.2), _hit("h2", -0.1)]
    notes = [_hit("n1", 1.5, "note")]
    links = [(_hit("l1", 0.0, "note"), "n1")]
    order = [(hit.record_id, via) for hit, via, _ in merge_by_score(history, notes, links)]
    assert order == [("n1", "curated"), ("l1", "link"), ("h1", "history"), ("h2", "history")]


def test_below_the_floor_is_dropped_with_its_links_and_ties_keep_history_first():
    history = [_hit("h1", 0.5), _hit("weak", -2.0)]
    notes = [_hit("n1", 0.5, "note"), _hit("n2", -3.0, "note")]
    links = [(_hit("l2", 0.0, "note"), "n2")]
    order = [hit.record_id for hit, _, _ in merge_by_score(history, notes, links)]
    assert order == ["h1", "n1"]
