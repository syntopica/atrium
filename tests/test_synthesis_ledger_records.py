"""`atrium synthesis recent|show`: newest records and spend, content only on show."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from atrium.cli import main
from atrium.ledger.synthesis_recent import synthesis_recent
from atrium.synthesize.synthesize_conversation import synthesize_conversation

SENTINEL = "a synthesized title that only show may print"
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC).timestamp()
DAY = 86_400


def _write(registry: Path, key: str, mtime: float, **fields) -> Path:
    record = {
        "job_key": key,
        "conversation_id": "conv-" + key[:4],
        "source": "claude-code",
        "episode_id": "ep-" + key[:4],
        "event_ids": ["e1", "e2", "e3"],
        "segmentation": "episode-texttiling-v1",
        "model_requested": "local-model-a",
        "model_resolved": "model-a:7b",
        "map_chunks": 1,
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "authored_at": "2026-09-01T00:00:00Z",
        "output": {
            "title": SENTINEL,
            "summary": "a summary",
            "facts": ["one", "two"],
            "open_ends": ["three"],
        },
        **fields,
    }
    path = registry / "records" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    os.utime(path, (mtime, mtime))
    return path


def _registry(tmp_path: Path) -> Path:
    registry = tmp_path / "synthesis"
    _write(registry, "a" * 32, NOW - 3 * DAY)
    _write(registry, "b" * 32, NOW - 60)
    _write(registry, "c" * 32, NOW - 3600, usage={"input_tokens": 7, "output_tokens": 3})
    _write(registry, "d" * 32, NOW - 40 * DAY)
    session = {"since": "2026-09-14T09:00:00Z", "until": "2026-09-14T10:00:00Z"}
    _write(
        registry,
        "e" * 32,
        NOW - 2 * DAY,
        segmentation="session-self-v1",
        session=session,
        event_ids=[],
        usage={"input_tokens": 0, "output_tokens": 0},
    )
    (registry / "records" / ("f" * 32 + ".tmp-1-2")).write_text("partial")
    (registry / "records" / ("0" * 32 + ".json")).write_text("{not json")
    return registry


def test_recent_lists_the_newest_records_without_content(tmp_path):
    document = synthesis_recent(_registry(tmp_path), NOW, 3, 14)
    assert SENTINEL not in json.dumps(document)
    assert document["schemaVersion"] == 1
    assert document["records"] == 6
    keys = [row["jobKey"] for row in document["recent"]]
    assert keys == ["b" * 32, "c" * 32]  # the malformed newest file is skipped
    first = document["recent"][0]
    assert first["kind"] == "episode"
    assert first["eventCount"] == 3
    assert (first["facts"], first["openEnds"]) == (2, 1)
    assert (first["inputTokens"], first["outputTokens"]) == (100, 10)
    assert first["modelResolved"] == "model-a:7b"
    assert first["durationMs"] is None
    assert first["writtenAt"] == "2026-09-14T11:59:00Z"


def test_a_session_record_carries_its_window(tmp_path):
    document = synthesis_recent(_registry(tmp_path), NOW, 10, 14)
    session = next(row for row in document["recent"] if row["kind"] == "session")
    assert session["session"] == {"since": "2026-09-14T09:00:00Z", "until": "2026-09-14T10:00:00Z"}
    assert session["eventCount"] == 0


def test_daily_totals_are_zero_filled_utc_days(tmp_path):
    daily = synthesis_recent(_registry(tmp_path), NOW, 1, 14)["daily"]
    assert len(daily) == 14
    assert daily[0]["day"] == "2026-09-01"
    assert daily[-1] == {
        "day": "2026-09-14",
        "records": 2,
        "inputTokens": 107,
        "outputTokens": 13,
    }
    by_day = {row["day"]: row for row in daily}
    assert by_day["2026-09-11"]["records"] == 1
    assert by_day["2026-09-12"] == {
        "day": "2026-09-12",
        "records": 1,
        "inputTokens": 0,
        "outputTokens": 0,
    }
    assert sum(row["records"] for row in daily) == 4  # the 40-day-old one is outside


def test_a_record_stamp_wins_over_its_mtime(tmp_path):
    registry = tmp_path / "synthesis"
    _write(registry, "a" * 32, NOW, synthesized_at="2026-09-13T08:00:00Z", duration_ms=1500)
    document = synthesis_recent(registry, NOW, 1, 2)
    assert document["recent"][0]["writtenAt"] == "2026-09-13T08:00:00Z"
    assert document["recent"][0]["durationMs"] == 1500
    assert [row["records"] for row in document["daily"]] == [1, 0]


def test_an_empty_registry_is_an_empty_document(tmp_path):
    document = synthesis_recent(tmp_path / "absent", NOW, 5, 3)
    assert document["records"] == 0
    assert document["recent"] == []
    assert document["lastPass"] is None
    assert [row["records"] for row in document["daily"]] == [0, 0, 0]


def test_show_prints_content_marked_as_content(tmp_path, monkeypatch, capsys):
    registry = _registry(tmp_path)
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    assert registry == tmp_path / "synthesis"
    assert main(["synthesis", "show", "--json", "--job-key", "b" * 32]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["content"]["title"] == SENTINEL
    assert document["content"]["openEnds"] == ["three"]
    assert SENTINEL not in json.dumps(document["record"])


def test_show_refuses_anything_but_a_registry_key(tmp_path, monkeypatch, capsys):
    _registry(tmp_path)
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    for key in ("../../etc/passwd", "9" * 32, "B" * 32):
        assert main(["synthesis", "show", "--json", "--job-key", key]) == 1
        assert json.loads(capsys.readouterr().out) == {"schemaVersion": 1, "error": "not_found"}


def test_recent_cli_prints_the_document(tmp_path, monkeypatch, capsys):
    _registry(tmp_path)
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    assert main(["synthesis", "recent", "--json", "--limit", "2", "--days", "3"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert len(document["daily"]) == 3
    assert SENTINEL not in json.dumps(document)


def test_new_records_carry_when_and_how_long(tmp_path):
    def producer(_system: str, _user: str, _tool: dict) -> dict:
        return {
            "input": {"title": "t", "summary": "s", "facts": [], "open_ends": []},
            "model": "fake",
            "usage": {"input_tokens": 5, "output_tokens": 2},
        }

    conversation = {
        "id": "c" * 64,
        "source": "claude-code",
        "schemaVersion": 2,
        "provenance": {"contentSha256": "a" * 64},
        "events": [{"id": "e1", "kind": "message", "role": "user", "text": "hello there"}],
    }
    synthesize_conversation(conversation, producer, "fake", tmp_path)
    [path] = (tmp_path / "records").glob("*.json")
    record = json.loads(path.read_text())
    assert isinstance(record["duration_ms"], int)
    assert record["duration_ms"] >= 0
    assert record["synthesized_at"].endswith("Z")
