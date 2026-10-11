"""Lane telemetry is private, best effort, and honest about coverage."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from atrium import cli
from atrium.adapters import atrium_context as context_module
from atrium.adapters import atrium_recall as recall_module
from atrium.adapters import atrium_search as search_module
from atrium.store.open_store import open_store
from atrium.telemetry.aggregate_lane_usage import aggregate_lane_usage
from atrium.telemetry.append_lane_event import append_lane_event


def test_concurrent_events_are_atomic_and_contain_no_query(tmp_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: append_lane_event(tmp_path, "cli.search", "auto"), range(100)))
    path = tmp_path / "lane-usage" / f"{datetime.now(UTC).date()}.jsonl"
    lines = path.read_text().splitlines()
    assert len(lines) == 100
    assert path.stat().st_mode & 0o777 == 0o600
    assert all(set(json.loads(line)) == {"ts", "entrypoint", "lane"} for line in lines)
    assert aggregate_lane_usage(tmp_path, 1)["lanes"]["auto"] == 100


def test_missing_window_is_no_coverage_and_partial_window_is_lower_bound(tmp_path):
    assert aggregate_lane_usage(tmp_path, 1)["coverage"] == "none"
    append_lane_event(tmp_path, "mcp.context", "words")
    single = aggregate_lane_usage(tmp_path, 1)
    assert single["coverage"] == "observed"
    assert single["lanes"]["substring"] == 0
    partial = aggregate_lane_usage(tmp_path, 2)
    assert partial["coverage"] == "partial"
    assert partial["lower_bound"] is True


def test_write_failure_warns_and_does_not_raise(tmp_path, capsys):
    (tmp_path / "lane-usage").write_text("not a directory")
    append_lane_event(tmp_path, "cli.recall", "recent")
    assert "lane telemetry unavailable" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "handler", "module", "lane"),
    [
        (["search", "private query", "--substring"], "run_search", cli, "substring"),
        (["context", "private query", "--lane", "words"], "run_context_cli", None, "words"),
        (["recall"], "run_recall", cli, "recent"),
    ],
)
def test_cli_entrypoints_append_once(tmp_path, monkeypatch, argv, handler, module, lane):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    if module is None:
        from atrium.context import run_context_cli as module

    monkeypatch.setattr(module, handler, lambda *args, **kwargs: 0)
    assert cli.main(argv) == 0
    status = aggregate_lane_usage(tmp_path, 1)
    assert status["events"] == 1
    assert status["lanes"][lane] == 1
    path = tmp_path / "lane-usage" / f"{datetime.now(UTC).date()}.jsonl"
    assert "private query" not in path.read_text()


def test_mcp_entrypoints_append_once(tmp_path, monkeypatch):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    monkeypatch.setattr(
        search_module, "open_store", lambda *args, **kwargs: sqlite3.connect(":memory:")
    )
    monkeypatch.setattr(search_module, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(search_module, "resident_embedder", lambda: None)
    monkeypatch.setattr(context_module, "context_from_index", lambda *args, **kwargs: {})
    monkeypatch.setattr(recall_module, "project_workspace", lambda cwd: None)
    search_module.atrium_search("private query")
    context_module.atrium_context("private query")
    recall_module.atrium_recall(str(tmp_path))
    status = aggregate_lane_usage(tmp_path, 1)
    assert status["events"] == 3
    assert status["entrypoints"] == {"mcp.search": 1, "mcp.context": 1, "mcp.recall": 1}


def test_status_lanes_reports_no_coverage_without_opening_index(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    assert cli.main(["status", "--lanes", "--days", "1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["coverage"] == "none"


def test_mcp_telemetry_does_not_modify_read_only_index(tmp_path, monkeypatch):
    index = tmp_path / "index.sqlite3"
    open_store(index).close()
    original = index.read_bytes()
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path / "state"))
    monkeypatch.setattr(search_module, "INDEX", index)
    monkeypatch.setattr(search_module, "search", lambda *args, **kwargs: [])
    search_module.atrium_search("private query", lane="words")
    assert index.read_bytes() == original
    assert aggregate_lane_usage(tmp_path / "state", 1)["events"] == 1
