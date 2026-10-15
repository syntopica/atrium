"""The query log becomes a list of unanswered questions and the records served most."""

import json
from datetime import date

from atrium.gaps.gap_report import gap_report
from atrium.gaps.is_gap import is_gap
from atrium.gaps.read_query_events import read_query_events


def _event(query, scores, status="ready", lane="reranked"):
    return {
        "ts": "2026-10-15T10:00:00+00:00",
        "query": query,
        "workspace": "[HOME]/p/atrium",
        "index_status": status,
        "evidence": [
            {"record_id": f"r{i}", "score": s, "lane": lane} for i, s in enumerate(scores)
        ],
    }


def test_nothing_returned_and_nothing_scoring_are_gaps_and_an_outage_is_not():
    assert is_gap(_event("q", []))
    assert is_gap(_event("q", [-3.0, -5.0]))
    assert not is_gap(_event("q", [-3.0, 2.0]))
    assert not is_gap(_event("q", [], status="unavailable"))
    assert not is_gap(_event("q", [0.001], lane="fused"))


def test_repeats_of_a_question_count_together_most_asked_first():
    events = [_event("Why  slow?", []), _event("why slow?", [-4.0]), _event("other", [])]
    report = gap_report(events, 10)
    assert [(gap["question"], gap["asked"]) for gap in report["gaps"]] == [
        ("Why  slow?", 2),
        ("other", 1),
    ]
    assert report["gaps"][0]["best"] == -4.0
    assert report["served"] == [{"record_id": "r0", "times": 1}]


def test_reading_skips_torn_lines_and_days_outside_the_window(tmp_path):
    (tmp_path / "2026-10-15.jsonl").write_text(json.dumps({"query": "a"}) + "\n{torn\n")
    (tmp_path / "2026-10-01.jsonl").write_text(json.dumps({"query": "old"}) + "\n")
    events = list(read_query_events(tmp_path, 3, date(2026, 10, 15)))
    assert [event["query"] for event in events] == ["a"]
