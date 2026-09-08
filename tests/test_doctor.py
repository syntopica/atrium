"""The doctor must fail when the memory would answer from a world that moved on."""

import json
import os
import sqlite3
import subprocess

from atrium.doctor import login_search_path as login_search_path_module
from atrium.doctor.archive_admissions import ArchiveAdmissions
from atrium.doctor.archive_freshness import archive_freshness
from atrium.doctor.archive_schema_coherence import archive_schema_coherence
from atrium.doctor.entry_point_health import entry_point_health
from atrium.doctor.index_coverage import index_coverage
from atrium.doctor.mcp_extra_requirements import mcp_extra_requirements
from atrium.doctor.read_archive_admissions import read_archive_admissions
from atrium.doctor.refresh_health import refresh_health
from atrium.doctor.run_doctor import run_doctor
from atrium.doctor.synthesis_coherence import synthesis_coherence


def _archive(path, manifest_version, record_versions):
    lines = [
        json.dumps(
            {
                "kind": "rocket-agents-conversation-export",
                "schemaVersion": manifest_version,
                "records": len(record_versions),
            }
        )
    ]
    for position, version in enumerate(record_versions):
        lines.append(json.dumps({"schemaVersion": version, "id": f"conv-{position}", "events": []}))
    path.write_text("\n".join(lines) + "\n")
    return path


def test_a_manifest_may_not_outrank_the_records_under_it(tmp_path):
    # The live state on 2026-08-31: manifest version 2 over version 1 records.
    # A reader trusting the header assumes qualified event ids and finds
    # unqualified ones, and nothing reported it.
    archive = _archive(tmp_path / "archive.jsonl", 2, [1, 1, 2])
    finding = archive_schema_coherence(archive)
    assert finding.severity == "broken"
    assert finding.detail["older"] == 2


def test_a_coherent_archive_passes(tmp_path):
    archive = _archive(tmp_path / "archive.jsonl", 2, [2, 2])
    assert archive_schema_coherence(archive).severity == "ok"


def test_a_dead_refresh_is_broken_not_merely_stale(tmp_path):
    stamp = tmp_path / "last-refresh"
    stamp.write_text("1000")
    assert refresh_health(stamp, now=1000 + 60).severity == "ok"
    assert refresh_health(stamp, now=1000 + 7200).severity == "warn"
    # Eleven days is what actually happened to the sync orchestrator, and every
    # run still printed "done".
    assert refresh_health(stamp, now=1000 + 11 * 86400).severity == "broken"


def test_a_missing_refresh_stamp_is_broken(tmp_path):
    assert refresh_health(tmp_path / "absent").severity == "broken"


def test_a_missing_archive_is_broken(tmp_path):
    assert archive_freshness(tmp_path / "absent").severity == "broken"


def _admissions(ids, admitting=None):
    admitting = ids if admitting is None else admitting
    return ArchiveAdmissions(all_ids=set(ids), admitting_ids=set(admitting))


def test_index_coverage_reports_the_gap_it_cannot_repair(tmp_path):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE records (conversation_id TEXT, provider TEXT)")
    connection.executemany(
        "INSERT INTO records VALUES (?, ?)",
        [("a", "codex"), ("b", "codex"), ("s", "synthesis")],
    )
    finding = index_coverage(connection, _admissions({"a", "b"}))
    assert finding.severity == "ok"

    # A tenth of the corpus missing still answers every query confidently.
    missing = {f"conv-{n}" for n in range(100)} | {"a", "b"}
    finding = index_coverage(connection, _admissions(missing))
    assert finding.severity == "broken"
    assert finding.detail["missing"] == 100


def test_a_conversation_that_admits_nothing_is_not_missing_coverage(tmp_path):
    """528 archived conversations here are pure tool calls and acknowledgements.
    Counting them as drift made this check warn on every single run, which is
    how an operator learns to ignore warnings."""
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE records (conversation_id TEXT, provider TEXT)")
    connection.executemany("INSERT INTO records VALUES (?, ?)", [("a", "codex")])
    finding = index_coverage(
        connection, _admissions({"a", *(f"chrome-{n}" for n in range(99))}, admitting={"a"})
    )
    assert finding.severity == "ok"
    assert finding.detail["missing"] == 0
    assert finding.detail["admits_nothing"] == 99


def test_the_admission_split_is_read_in_one_pass(tmp_path):
    archive = tmp_path / "archive.jsonl"
    body = "a sentinel passage long enough to be no acknowledgement"
    lines = [json.dumps({"kind": "rocket-agents-conversation-export", "records": 2})]
    lines.append(
        json.dumps(
            {
                "id": "real",
                "provenance": {"contentSha256": "s"},
                "events": [{"id": "e", "kind": "message", "role": "user", "text": body}],
            }
        )
    )
    lines.append(
        json.dumps(
            {
                "id": "chrome",
                "provenance": {"contentSha256": "s"},
                "events": [{"id": "t", "kind": "tool_result", "role": "user", "text": body}],
            }
        )
    )
    archive.write_text("\n".join(lines) + "\n")
    admissions = read_archive_admissions(archive)
    assert admissions.all_ids == {"real", "chrome"}
    assert admissions.admitting_ids == {"real"}


def test_synthesis_orphans_are_reported_never_deleted(tmp_path):
    records = tmp_path / "records"
    records.mkdir()
    (records / "one.json").write_text(json.dumps({"conversation_id": "gone", "episode_id": "e"}))
    finding = synthesis_coherence(tmp_path, {"present"})
    assert finding.severity == "warn"
    assert finding.detail["orphan_conversations"] == ["gone"]
    assert (records / "one.json").exists(), "paid model output is never removed by a check"


def test_reading_the_archive_skips_the_manifest(tmp_path):
    archive = _archive(tmp_path / "archive.jsonl", 2, [2, 2, 2])
    assert read_archive_admissions(archive).all_ids == {"conv-0", "conv-1", "conv-2"}


def _wrapper(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    wrapper = directory / name
    wrapper.write_text("#!/bin/sh\nexec uv run --project ~/p/atrium atrium \"$@\"\n")
    wrapper.chmod(0o755)
    return wrapper


def _health(tmp_path, search_path, **overrides):
    """The MCP half held at its healthy shape, so a CLI test asserts only the CLI."""
    fixed = {"scripts": {"atrium-mcp": "atrium.doctor.finding:Finding"}, "requirements": ["mcp>=2.1"]}
    return entry_point_health(search_path, hostname="mini", **{**fixed, **overrides})


def test_both_documented_entry_points_resolving_is_not_a_finding(tmp_path):
    _wrapper(tmp_path / "bin", "atrium")
    finding = _health(tmp_path, str(tmp_path / "bin"))
    assert finding.severity == "ok"
    assert finding.detail["hostname"] == "mini"
    assert finding.detail["command"] == str(tmp_path / "bin" / "atrium")
    assert finding.detail["mcp_extra"] == ["mcp>=2.1"]


def test_a_cli_missing_from_path_names_the_machine(tmp_path):
    """The live state until 2026-09-07: the index was all-green and every session
    following the documented `atrium search --project .` got `command not found`."""
    finding = _health(tmp_path, str(tmp_path / "empty"))
    assert finding.severity == "broken"
    assert "mini" in finding.summary
    assert finding.detail["missing"] == ["atrium is not on PATH a login shell would use"]


def test_the_venv_the_doctor_runs_under_does_not_answer_for_a_login_shell(tmp_path, monkeypatch):
    """The regression this check exists for: `uv run --project ~/p/atrium` prepends
    the venv bin, where the console script exists by construction. Asked of the
    inherited PATH the check is green exactly while no caller can reach the CLI."""
    venv = tmp_path / "venv" / "bin"
    _wrapper(venv, "atrium")
    monkeypatch.setattr(login_search_path_module.sysconfig, "get_path", lambda _name: str(venv))
    monkeypatch.setenv("PATH", os.pathsep.join([str(venv), str(tmp_path / "empty")]))
    finding = _health(tmp_path, None)
    assert finding.severity == "broken"
    assert "not on PATH a login shell would use" in finding.summary
    assert str(venv) not in finding.detail["search_path"]


def test_a_directory_shadowing_the_wrapper_is_reported_as_such(tmp_path):
    """`bootstrap.sh` linked every top-level `bin/*` entry, so a fresh machine got
    ~/.local/bin/atrium pointing at the directory holding the wrapper. It is on
    PATH, it is not runnable, and shutil.which steps straight over it."""
    (tmp_path / "bin" / "atrium").mkdir(parents=True)
    finding = _health(tmp_path, str(tmp_path / "bin"))
    assert finding.severity == "broken"
    assert "is a directory" in finding.summary


def test_a_wrapper_that_lost_its_exec_bit_is_not_reported_as_resolving(tmp_path):
    """Present on PATH and unusable is the failure class the check exists for."""
    wrapper = _wrapper(tmp_path / "bin", "atrium")
    wrapper.chmod(0o644)
    finding = _health(tmp_path, str(tmp_path / "bin"))
    assert finding.severity == "broken"
    assert "is not executable" in finding.summary


def test_a_dangling_symlink_is_not_reported_as_absent(tmp_path):
    """`exists()` is false for a broken link, which reads as "not on PATH" and
    sends the operator looking for a wrapper that is right there, pointing away."""
    directory = tmp_path / "bin"
    directory.mkdir()
    (directory / "atrium").symlink_to(tmp_path / "gone")
    finding = _health(tmp_path, str(directory))
    assert finding.severity == "broken"
    assert "is a broken symlink" in finding.summary


def test_an_unusable_candidate_does_not_hide_a_working_wrapper_further_along(tmp_path):
    """A POSIX shell skips it and keeps walking PATH; stopping early paints a
    machine that runs the real wrapper fine as broken, and fails the whole run."""
    (tmp_path / "shadow" / "atrium").mkdir(parents=True)
    _wrapper(tmp_path / "bin", "atrium")
    path = os.pathsep.join([str(tmp_path / "shadow"), str(tmp_path / "bin")])
    assert subprocess.run(["/bin/sh", "-c", "command -v atrium"], env={"PATH": path}, check=False).returncode == 0
    finding = _health(tmp_path, path)
    assert finding.severity == "warn"
    assert finding.detail["command"] == str(tmp_path / "bin" / "atrium")
    assert finding.detail["shadowed_by"] == [f"{tmp_path / 'shadow' / 'atrium'} is a directory, not the wrapper"]


def test_an_uninstalled_mcp_console_script_is_broken(tmp_path):
    _wrapper(tmp_path / "bin", "atrium")
    finding = _health(tmp_path, str(tmp_path / "bin"), scripts={"atrium": "atrium.cli:main"})
    assert finding.severity == "broken"
    assert finding.detail["missing"] == ["atrium-mcp is not an installed console script"]


def test_an_mcp_entry_point_naming_a_module_that_moved_is_broken(tmp_path):
    _wrapper(tmp_path / "bin", "atrium")
    scripts = {"atrium-mcp": "atrium.adapters.moved_away:main"}
    finding = _health(tmp_path, str(tmp_path / "bin"), scripts=scripts)
    assert finding.severity == "broken"
    assert "which does not resolve" in finding.summary
    assert finding.detail["mcp_entry_point"] == "atrium.adapters.moved_away:main"


def test_an_mcp_extra_missing_from_the_installed_metadata_is_broken(tmp_path):
    """`uv run --extra mcp --directory ~/p/atrium atrium-mcp` is what both
    `.claude.json` files spawn, and uv refuses an extra it cannot find."""
    _wrapper(tmp_path / "bin", "atrium")
    finding = _health(tmp_path, str(tmp_path / "bin"), requirements=[])
    assert finding.severity == "broken"
    assert "the mcp extra declares no requirements" in finding.summary


def test_the_mcp_extra_is_read_off_this_distribution():
    requirements = mcp_extra_requirements()
    # The shape, not the pin: bumping `mcp>=2.1` in pyproject.toml is not a
    # behaviour change and must not break this test.
    assert requirements and all(r.startswith("mcp") for r in requirements)


def test_the_doctor_leads_with_the_entry_points_and_a_dead_path_fails_it(tmp_path, monkeypatch):
    """The finding is first because an index nobody can reach makes every number
    under it academic -- and it is now what can turn a whole run red."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    findings = run_doctor(tmp_path / "index.db", tmp_path / "gone.jsonl", tmp_path / "s", tmp_path)
    assert findings[0].check == "entrypoints"
    assert findings[0].severity == "broken"
