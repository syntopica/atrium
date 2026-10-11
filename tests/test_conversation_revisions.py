"""Revisions let an unchanged conversation skip its read-back, and keep automation out.

The synthesis lane runs codex in a temporary directory, and every such run was
archived and indexed as if it were work: 43,085 of 54,026 conversations on
2026-10-11. The ingest now refuses them, the synthesis ingest drops what was
synthesized from them, and an index built before the rule is cleaned by the next
full ingest.
"""

import json

from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.doctor.archive_admissions import ArchiveAdmissions
from atrium.doctor.index_coverage import index_coverage
from atrium.ingest.is_excluded_automation import is_excluded_automation
from atrium.store.open_store import open_store
from atrium.store.revisions_backfilled import revisions_backfilled
from atrium.synthesize.population_report import population_report
from atrium.synthesize.write_record import write_record

AUTOMATION = "/var/folders/ab/xy12z/T/atrium-codex-k3j9"
LONG = "a durable decision, long enough to be kept as a record of its own"


def _conversation(conversation_id, text=LONG, source="pi", workspace="/Users/u/p/proj"):
    return {
        "id": conversation_id,
        "source": source,
        "workspace": workspace,
        "startedAt": "2026-10-01T00:00:00Z",
        "provenance": {"contentSha256": f"sha-{conversation_id}-{len(text)}"},
        "events": [{"id": "e1", "kind": "message", "role": "assistant", "text": text}]
        if text
        else [],
    }


def _write_archive(path, conversations):
    lines = [json.dumps({"kind": "rocket-agents-conversation-export", "records": 0})]
    lines += [json.dumps(c) for c in conversations]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _synthesis(conversation_id, episode="ep-1"):
    return {
        "job_key": f"job-{conversation_id}-{episode}",
        "conversation_id": conversation_id,
        "episode_id": f"{conversation_id}-{episode}",
        "model_requested": "codex-cli-default",
        "authored_at": "2026-10-01T00:00:00Z",
        "output": {"title": "Title", "summary": LONG, "facts": [], "open_ends": []},
    }


def _count(index, conversation_id):
    connection = open_store(index, read_only=True)
    try:
        sql = load_test_sql("revisions/count_conversation_records")
        return connection.execute(sql, (conversation_id,)).fetchone()[0]
    finally:
        connection.close()


def _revision(index, conversation_id):
    connection = open_store(index, read_only=True)
    try:
        sql = load_test_sql("revisions/select_revision")
        return connection.execute(sql, (conversation_id,)).fetchone()
    finally:
        connection.close()


def _state(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    return state, state / "index.sqlite3", tmp_path / "archive.jsonl"


def _embed_everything(index):
    connection = open_store(index)
    try:
        with connection:
            for conversation_id in ("keep", "synthesis/keep"):
                ids = connection.execute(
                    load_test_sql("revisions/select_record_ids"), (conversation_id,)
                ).fetchall()
                for (record_id,) in ids:
                    connection.execute(load_test_sql("insert_vector"), (record_id, b"\0" * 8))
    finally:
        connection.close()


def _vectors(index):
    connection = open_store(index, read_only=True)
    try:
        return connection.execute(load_test_sql("count_vectors")).fetchone()[0]
    finally:
        connection.close()


def test_only_the_synthesis_lanes_scratch_directory_is_automation():
    assert is_excluded_automation("codex", AUTOMATION)
    assert is_excluded_automation("codex", "/private" + AUTOMATION + "/")
    assert not is_excluded_automation("claude", AUTOMATION)
    assert not is_excluded_automation("codex", "/var/folders/ab/xy12z/T/other-tool-k3j9")
    assert not is_excluded_automation("codex", AUTOMATION + "/nested")
    assert not is_excluded_automation("codex", None)


def test_an_unchanged_conversation_is_skipped_and_keeps_its_vectors(tmp_path, monkeypatch):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("keep"), _conversation("edit")])
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    _embed_everything(index)
    before = _vectors(index)
    _write_archive(archive, [_conversation("keep"), _conversation("edit", LONG + " corrected")])
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    assert _vectors(index) == before
    assert _count(index, "edit") == 1
    assert _revision(index, "keep")[0] == "indexed"


def test_a_corrected_conversation_is_rewritten(tmp_path, monkeypatch, capsys):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("edit")])
    main(["--index", str(index), "ingest", str(archive)])
    _write_archive(archive, [_conversation("edit", LONG + " corrected")])
    capsys.readouterr()
    main(["--index", str(index), "ingest", str(archive)])
    assert "1 records written" in capsys.readouterr().out


def test_an_empty_conversation_is_recorded_as_empty(tmp_path, monkeypatch):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("blank", text="")])
    main(["--index", str(index), "ingest", str(archive)])
    assert _revision(index, "blank")[0] == "empty"


def test_a_full_sweep_drops_rows_and_revision_and_a_partial_one_keeps_both(tmp_path, monkeypatch):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("gone"), _conversation("stays")])
    main(["--index", str(index), "ingest", str(archive)])
    _write_archive(archive, [_conversation("stays")])
    main(["--index", str(index), "ingest", "--partial", str(archive)])
    assert _count(index, "gone") == 1
    assert _revision(index, "gone") is not None
    main(["--index", str(index), "ingest", str(archive)])
    assert _count(index, "gone") == 0
    assert _revision(index, "gone") is None


def test_only_a_full_ingest_marks_the_revisions_complete(tmp_path, monkeypatch):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("one")])
    main(["--index", str(index), "ingest", "--partial", str(archive)])
    connection = open_store(index)
    assert not revisions_backfilled(connection)
    connection.close()
    main(["--index", str(index), "ingest", str(archive)])
    connection = open_store(index)
    assert revisions_backfilled(connection)
    connection.close()


def test_automation_is_indexed_as_nothing_and_its_synthesis_is_dropped(tmp_path, monkeypatch):
    state, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(
        archive,
        [_conversation("keep"), _conversation("auto", source="codex", workspace=AUTOMATION)],
    )
    main(["--index", str(index), "ingest", str(archive)])
    assert _count(index, "auto") == 0
    assert _revision(index, "auto")[0] == "excluded_automation"
    for conversation_id in ("keep", "auto"):
        record = _synthesis(conversation_id)
        write_record(state / "synthesis", record["job_key"], record)
    assert main(["ingest-synthesis"]) == 0
    assert _count(index, "synthesis/keep") == 1
    assert _count(index, "synthesis/auto") == 0
    rows = population_report(state / "synthesis", {"keep-ep-1"}, {"auto"})
    assert [(row["intended"], row["indexed"], row["excluded"]) for row in rows] == [(1, 1, 1)]


def test_the_next_ingest_cleans_an_index_built_before_the_rule(tmp_path, monkeypatch):
    """Rows, synthesis and vectors of automation indexed before the exclusion all go."""
    state, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(
        archive,
        [
            _conversation("keep"),
            _conversation("auto", source="codex", workspace="/private" + AUTOMATION),
        ],
    )
    monkeypatch.setattr(
        "atrium.commands.run_ingest.is_excluded_automation", lambda provider, workspace: False
    )
    main(["--index", str(index), "ingest", str(archive)])
    for conversation_id in ("keep", "auto"):
        record = _synthesis(conversation_id)
        write_record(state / "synthesis", record["job_key"], record)
    main(["ingest-synthesis"])
    assert _count(index, "auto") == 1
    assert _count(index, "synthesis/auto") == 1
    connection = open_store(index)
    with connection:
        for conversation_id in ("auto", "synthesis/auto"):
            for (record_id,) in connection.execute(
                load_test_sql("revisions/select_record_ids"), (conversation_id,)
            ).fetchall():
                connection.execute(load_test_sql("insert_vector"), (record_id, b"\0" * 8))
    connection.close()
    monkeypatch.undo()
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    main(["--index", str(index), "ingest", str(archive)])
    main(["ingest-synthesis"])
    assert _count(index, "auto") == 0
    assert _count(index, "synthesis/auto") == 0
    assert _vectors(index) == 0
    assert _count(index, "keep") == 1
    assert _count(index, "synthesis/keep") == 1


def test_an_id_rewritten_by_another_provider_is_not_skipped(tmp_path, monkeypatch):
    """Rows are keyed by conversation id alone; a stale revision must not vouch for them."""
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("x", source="claude-code")])
    main(["--index", str(index), "ingest", str(archive)])
    _write_archive(
        archive,
        [
            _conversation("y", source="claude-code"),
            _conversation("x", text=LONG + " from pi", source="pi"),
            _conversation("x", source="claude-code"),
        ],
    )
    main(["--index", str(index), "ingest", "--partial", str(archive)])
    connection = open_store(index, read_only=True)
    try:
        (text,) = connection.execute(load_test_sql("revisions/select_text"), ("x",)).fetchone()
    finally:
        connection.close()
    assert text == LONG


def test_a_source_with_no_workspace_is_not_given_the_registrys(tmp_path, monkeypatch):
    state, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(archive, [_conversation("bare", workspace=None)])
    main(["--index", str(index), "ingest", str(archive)])
    record = dict(_synthesis("bare"), workspace="/Users/u/p/elsewhere")
    write_record(state / "synthesis", record["job_key"], record)
    main(["ingest-synthesis"])
    connection = open_store(index, read_only=True)
    try:
        (workspace,) = connection.execute(
            load_test_sql("revisions/select_workspace"), ("synthesis/bare",)
        ).fetchone()
    finally:
        connection.close()
    assert workspace is None


def test_doctor_does_not_count_excluded_automation_as_missing(tmp_path, monkeypatch):
    _state_dir, index, archive = _state(tmp_path, monkeypatch)
    _write_archive(
        archive,
        [_conversation("keep"), _conversation("auto", source="codex", workspace=AUTOMATION)],
    )
    main(["--index", str(index), "ingest", str(archive)])
    connection = open_store(index, read_only=True)
    try:
        finding = index_coverage(
            connection,
            ArchiveAdmissions(all_ids={"keep", "auto"}, admitting_ids={"keep", "auto"}),
        )
    finally:
        connection.close()
    assert finding.severity == "ok"
    assert finding.detail["missing"] == 0
    assert finding.detail["excluded_automation"] == 1
