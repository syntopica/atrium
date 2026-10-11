"""Ingest a scribe pending slice and propagate a scribe erasure plan.

The fixtures are verbatim copies of scribe's ``fixtures/archive-contract/v2/``
(scribe ``31d70f8``): ``pending-slice.jsonl`` holds only the Claude Code
conversation of ``export.jsonl``; ``erasure-plan.json`` is an applied plan that
erases that same conversation. Replace them, never edit them.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.erase.read_erasure_plan import read_erasure_plan
from atrium.store.open_store import open_store
from atrium.synthesize.write_record import write_record

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT = FIXTURES / "scribe_archive_contract_v2.jsonl"
SLICE = FIXTURES / "scribe_pending_slice_v2.jsonl"
PLAN = FIXTURES / "scribe_erasure_plan_v2.json"
CLAUDE = "e322478280e4391e62a625d08b33bd2011e87e7323bc721290a389b7ecca9504"
SUMMARY = "a durable decision, long enough to be kept as a record of its own"


def _codex_id():
    lines = EXPORT.read_text(encoding="utf-8").splitlines()[1:]
    return next(json.loads(line)["id"] for line in lines if json.loads(line)["source"] == "codex")


def _query(index, sql, *parameters):
    connection = open_store(index, read_only=True)
    try:
        return connection.execute(load_test_sql(sql), parameters).fetchall()
    finally:
        connection.close()


def _count(index, conversation_id):
    return _query(index, "revisions/count_conversation_records", conversation_id)[0][0]


def _embed(index, conversation_id):
    connection = open_store(index)
    with connection:
        for (record_id,) in connection.execute(
            load_test_sql("revisions/select_record_ids"), (conversation_id,)
        ).fetchall():
            connection.execute(load_test_sql("insert_vector"), (record_id, b"\0" * 8))
    connection.close()


def _synthesis(conversation_id):
    return {
        "job_key": f"job-{conversation_id[:12]}",
        "conversation_id": conversation_id,
        "episode_id": f"{conversation_id[:12]}-ep",
        "model_requested": "codex-cli-default",
        "authored_at": "2026-10-01T00:00:00Z",
        "output": {"title": "Title", "summary": SUMMARY, "facts": [], "open_ends": []},
    }


@pytest.fixture
def state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    return state


def test_a_partial_slice_writes_its_conversation_and_touches_nothing_else(state):
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", str(EXPORT)])
    codex = _codex_id()
    _embed(index, codex)
    before = _query(index, "select_all_records")
    vectors = _query(index, "count_vectors")
    main(["--index", str(index), "ingest", "--partial", str(SLICE)])
    assert _count(index, CLAUDE) == 3
    assert [row for row in _query(index, "select_all_records") if CLAUDE not in row] == [
        row for row in before if CLAUDE not in row
    ]
    assert _query(index, "count_vectors") == vectors


def test_a_partial_slice_into_an_empty_index_holds_only_its_conversation(state):
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", "--partial", str(SLICE)])
    assert _count(index, CLAUDE) == 3
    assert _count(index, _codex_id()) == 0


TARGET = json.loads(PLAN.read_text(encoding="utf-8"))["toGenerationId"]


def test_the_plan_names_the_erased_conversation_and_its_target_generation():
    plan = read_erasure_plan(PLAN)
    assert plan.conversation_ids == (CLAUDE,)
    assert plan.to_generation_id == TARGET


def test_an_unapplied_plan_is_refused(tmp_path):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    del plan["toGenerationId"]
    unapplied = tmp_path / "plan.json"
    unapplied.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ValueError, match="not been applied"):
        read_erasure_plan(unapplied)


def _erasable(state):
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", str(EXPORT)])
    registry = state / "synthesis"
    codex = _codex_id()
    for conversation_id in (CLAUDE, codex):
        record = _synthesis(conversation_id)
        write_record(registry, record["job_key"], record)
    backup = registry / "records.bak-20260101"
    backup.mkdir()
    erased = _synthesis(CLAUDE)
    (backup / f"{erased['job_key']}.json").write_text(json.dumps(erased), encoding="utf-8")
    (registry / "partials").mkdir()
    (registry / "partials" / "cached.json").write_text("{}", encoding="utf-8")
    (state / "dense-matrix.npz").write_bytes(b"stale")
    curation = state / "curation"
    curation.mkdir()
    rows = [
        {"candidate_id": "c-erased", "sources": [{"conversation_id": CLAUDE}], "text": "erased"},
        {"candidate_id": "c-kept", "sources": [{"conversation_id": codex}], "text": "kept"},
    ]
    (curation / "candidates.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    erased_job = _synthesis(CLAUDE)["job_key"]
    (curation / "quarantine.jsonl").write_text(
        json.dumps({"text": "erased fact", "reason": "r", "job_key": erased_job}) + "\n",
        encoding="utf-8",
    )
    run = curation / "proposals" / "20260101T000000Z"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"refused": [{"candidate_id": "c-erased"}]}))
    (run / "review.md").write_text("- erased claim text\n")
    kept_run = curation / "proposals" / "20260102T000000Z"
    kept_run.mkdir()
    (kept_run / "manifest.json").write_text(json.dumps({"refused": [{"candidate_id": "c-kept"}]}))
    (curation / "pairs.jsonl").write_text(
        json.dumps({"left": "c-erased", "right": "c-kept"}) + "\n", encoding="utf-8"
    )
    (curation / "candidate-ids.jsonl").write_text('"c-erased"\n"c-kept"\n', encoding="utf-8")
    np.arange(2 * 384, dtype=np.float32).tofile(curation / "candidates.f32")
    main(["--index", str(index), "ingest-synthesis"])
    for conversation_id in (CLAUDE, f"synthesis/{CLAUDE}", codex):
        _embed(index, conversation_id)
    return index, registry, backup, codex


def test_without_apply_erase_reports_and_changes_nothing(state, capsys):
    index, registry, _backup, _codex = _erasable(state)
    capsys.readouterr()
    assert main(["--index", str(index), "erase", "--plan", str(PLAN)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "applied": False,
        "conversations": 1,
        "curation_candidates": 1,
        "record_files": 2,
    }
    assert _count(index, f"synthesis/{CLAUDE}") == 1
    assert len(list((registry / "records").glob("*.json"))) == 2
    assert (state / "dense-matrix.npz").exists()


def test_erase_removes_every_derived_trace_and_keeps_the_rest(state, capsys, monkeypatch):
    index, registry, _backup, codex = _erasable(state)
    capsys.readouterr()
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))
    assert main(["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["index_rows_removed"] == 4
    assert report["partials_removed"] == 1
    assert _count(index, CLAUDE) == 0
    assert _count(index, f"synthesis/{CLAUDE}") == 0
    assert _query(index, "count_vectors")[0][0] == _count(index, codex)
    assert _count(index, f"synthesis/{codex}") == 1
    remaining = [
        json.loads(p.read_text())["conversation_id"] for p in registry.glob("records*/*.json")
    ]
    assert remaining == [codex]
    assert not (state / "dense-matrix.npz").exists()
    assert report["curation"] == {
        "files": 0,
        "lines": 3,
        "matrix_rows": 1,
        "proposal_runs": 1,
    }
    assert [p.name for p in (state / "curation" / "proposals").iterdir()] == ["20260102T000000Z"]
    assert (state / "curation" / "quarantine.jsonl").read_text() == ""
    curation = state / "curation"
    assert [json.loads(r)["candidate_id"] for r in (curation / "candidates.jsonl").open()] == [
        "c-kept"
    ]
    assert (curation / "pairs.jsonl").read_text() == ""
    assert (curation / "candidate-ids.jsonl").read_text() == '"c-kept"\n'
    matrix = np.fromfile(curation / "candidates.f32", dtype=np.float32).reshape(-1, 384)
    assert matrix.tolist() == np.arange(384, 2 * 384, dtype=np.float32).reshape(1, 384).tolist()
    main(["--index", str(index), "ingest-synthesis"])
    assert _count(index, f"synthesis/{CLAUDE}") == 0


def _archive_at(state, generation):
    """An export materialized from ``generation``: the manifest names it."""
    lines = EXPORT.read_text(encoding="utf-8").splitlines()
    manifest = json.loads(lines[0])
    if generation:
        manifest["generationId"] = generation
    kept = [line for line in lines[1:] if json.loads(line)["id"] != CLAUDE]
    path = state / f"archive-{generation}.jsonl"
    path.write_text("\n".join([json.dumps(manifest), *kept]) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("generation", [None, "an-older-generation"])
def test_apply_refuses_unless_the_archive_is_at_the_plans_target(state, monkeypatch, generation):
    index, registry, _backup, _codex = _erasable(state)
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, generation))
    assert main(["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]) == 1
    assert _count(index, CLAUDE) == 3
    assert len(list((registry / "records").glob("*.json"))) == 2


def test_an_index_outside_the_configured_instance_is_refused(state, monkeypatch):
    index, registry, _backup, _codex = _erasable(state)
    other = state / "copy.sqlite3"
    other.write_bytes(index.read_bytes())
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))
    assert main(["--index", str(other), "erase", "--plan", str(PLAN), "--apply"]) == 2
    assert len(list((registry / "records").glob("*.json"))) == 2


def test_a_run_that_failed_partway_is_finished_by_running_it_again(state, monkeypatch):
    index, registry, _backup, _codex = _erasable(state)
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))

    def broken(*_args):
        raise OSError("disk full")

    monkeypatch.setattr("atrium.commands.run_erase.scrub_curation", broken)
    erase = ["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]
    with pytest.raises(OSError, match="disk full"):
        main(erase)
    assert len(list(registry.glob("records*/*.json"))) == 1
    main(["--index", str(index), "ingest-synthesis"])
    assert _count(index, f"synthesis/{CLAUDE}") == 0
    monkeypatch.undo()
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))
    assert main(erase) == 0
    assert (state / "curation" / "quarantine.jsonl").read_text() == ""
    assert len(list(registry.glob("records*/*.json"))) == 1


def test_apply_refuses_while_a_refresh_holds_the_instance(state, monkeypatch):
    import fcntl

    index, registry, _backup, _codex = _erasable(state)
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))
    with (state / "refresh.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert main(["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]) == 3
    assert _count(index, CLAUDE) == 3
    assert len(list((registry / "records").glob("*.json"))) == 2


def test_a_matrix_misaligned_with_its_ids_is_dropped(tmp_path):
    from atrium.erase.scrub_aligned_matrix import scrub_aligned_matrix

    ids, matrix = tmp_path / "ids.jsonl", tmp_path / "m.f32"
    ids.write_text('"a"\n"b"\n', encoding="utf-8")
    np.zeros((1, 384), dtype=np.float32).tofile(matrix)
    assert scrub_aligned_matrix(ids, matrix, {"zzz"}) == 1
    assert not ids.exists()
    assert not matrix.exists()


def test_an_archive_that_moved_past_the_target_is_accepted(state, monkeypatch):
    index, _registry, _backup, _codex = _erasable(state)
    later = _archive_at(state, "a-later-generation")
    lines = later.read_text(encoding="utf-8").splitlines()
    manifest = json.loads(lines[0])
    manifest["generationLineage"] = [TARGET]
    later.write_text("\n".join([json.dumps(manifest), *lines[1:]]) + "\n", encoding="utf-8")
    monkeypatch.setattr("atrium.cli.archive_path", lambda: later)
    assert main(["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]) == 0
    assert _count(index, f"synthesis/{CLAUDE}") == 0


def test_half_a_matrix_pair_is_dropped(tmp_path):
    from atrium.erase.scrub_aligned_matrix import scrub_aligned_matrix

    matrix = tmp_path / "m.f32"
    np.zeros((2, 384), dtype=np.float32).tofile(matrix)
    assert scrub_aligned_matrix(tmp_path / "ids.jsonl", matrix, {"zzz"}) == 2
    assert not matrix.exists()


def test_erase_leaves_no_erased_text_in_the_index_files(state, monkeypatch):
    """Deleted SQLite rows survive in freed pages, the WAL and FTS segments
    unless the delete overwrites them; the bytes on disk are the test."""
    index, _registry, _backup, _codex = _erasable(state)
    monkeypatch.setattr("atrium.cli.archive_path", lambda: _archive_at(state, TARGET))
    assert main(["--index", str(index), "erase", "--plan", str(PLAN), "--apply"]) == 0
    stored = b"".join(
        path.read_bytes() for path in index.parent.glob(index.name + "*") if path.is_file()
    )
    assert b"exits with status 3" not in stored
    assert b"deploy script" not in stored
