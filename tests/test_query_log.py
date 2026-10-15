"""Each context answer leaves one query-log line beside the registry, never its text."""

import json

from atrium.telemetry.append_query_event import append_query_event

RESPONSE = {
    "query": "why did the refresh slow down",
    "scope": {"workspace": "[HOME]/p/atrium"},
    "route": {"requested_lane": "auto"},
    "index_status": "ready",
    "served_by": "service",
    "evidence": [
        {"record_id": "r1", "score": 2.5, "lane": "reranked", "via": "history", "text": "secret"}
    ],
    "warnings": [],
}


def test_one_line_per_answer_with_ids_and_scores_only(tmp_path):
    append_query_event(tmp_path, RESPONSE, "cli.context")
    append_query_event(tmp_path, RESPONSE, "mcp.context")
    (log,) = (tmp_path / "synthesis" / "queries").iterdir()
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["entrypoint"] for line in lines] == ["cli.context", "mcp.context"]
    assert lines[0]["evidence"] == [
        {"record_id": "r1", "score": 2.5, "lane": "reranked", "via": "history"}
    ]
    assert "secret" not in log.read_text()
    assert oct(log.stat().st_mode & 0o777) == "0o600"


def test_an_unwritable_log_never_fails_the_answer(tmp_path, capsys):
    (tmp_path / "synthesis").write_text("not a directory")
    append_query_event(tmp_path, RESPONSE, "cli.context")
    assert "query log unavailable" in capsys.readouterr().err


def test_a_credential_in_the_question_is_redacted_before_it_is_logged(tmp_path):
    token = "Bearer " + "x" * 32
    append_query_event(
        tmp_path, {**RESPONSE, "query": "why does " + token + " fail"}, "cli.context"
    )
    (log,) = (tmp_path / "synthesis" / "queries").iterdir()
    (line,) = [json.loads(line) for line in log.read_text().splitlines()]
    assert line["query"] == "why does Bearer [REDACTED:token] fail"
