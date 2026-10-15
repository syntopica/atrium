"""The index records its archive generation, and a rebuild compares against live.

Fixtures are scribe's ``fixtures/archive-contract/v2/``, vendored for the
segment contract tests.
"""

import json
from pathlib import Path

import pytest

from atrium.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT = FIXTURES / "scribe_archive_contract_v2.jsonl"
SLICE = FIXTURES / "scribe_pending_slice_v2.jsonl"
MATERIALIZED = FIXTURES / "scribe_materialized_after_erasure_v2.jsonl"
TARGET = json.loads((FIXTURES / "scribe_erasure_plan_v2.json").read_text(encoding="utf-8"))[
    "toGenerationId"
]


@pytest.fixture
def state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    return state


def _generation_check(index, inventory):
    from atrium.doctor.archive_generation_freshness import archive_generation_freshness
    from atrium.store.open_store import open_store

    connection = open_store(index, read_only=True)
    try:
        return archive_generation_freshness(connection, inventory)
    finally:
        connection.close()


def test_a_full_ingest_records_its_generation_and_a_slice_does_not(state):
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", str(MATERIALIZED)])
    current = {"generationId": TARGET, "pendingDeliveries": 0}
    assert _generation_check(index, current).code == "archive_generation_current"
    main(["--index", str(index), "ingest", "--partial", str(SLICE)])
    assert _generation_check(index, current).code == "archive_generation_current"
    pending = {"generationId": TARGET, "pendingDeliveries": 2}
    assert _generation_check(index, pending).code == "archive_deliveries_pending"
    moved = {"generationId": "f" * 64, "pendingDeliveries": 0}
    assert _generation_check(index, moved).severity == "warn"
    assert _generation_check(index, moved).code == "archive_generation_stale"
    main(["--index", str(index), "ingest", str(EXPORT)])
    assert _generation_check(index, current).detail["indexed"] is None


def test_parity_reports_equal_rebuilds_and_names_what_differs(state, tmp_path, capsys):
    live = state / "index.sqlite3"
    main(["--index", str(live), "ingest", str(EXPORT)])
    same = tmp_path / "same.sqlite3"
    main(["--index", str(same), "ingest", str(EXPORT)])
    capsys.readouterr()
    assert main(["--index", str(live), "parity", str(same)]) == 0
    assert json.loads(capsys.readouterr().out)["equal"] is True

    after = tmp_path / "after.sqlite3"
    main(["--index", str(after), "ingest", str(MATERIALIZED)])
    capsys.readouterr()
    assert main(["--index", str(live), "parity", str(after)]) == 1
    report = json.loads(capsys.readouterr().out)
    only_live = sum(row["only_live"]["count"] for row in report["records"].values())
    assert only_live > 0
    assert report["fts"] == {"test": "fts_ranked_probe_passed", "live": "fts_ranked_probe_passed"}
