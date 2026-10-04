"""`atrium synthesis passes`: every pass end, including the ones the time box kills."""

import json
from datetime import datetime

from atrium.cli import main
from atrium.ledger.parse_pass_log import parse_pass_log
from atrium.ledger.pass_progress import pass_progress
from atrium.ledger.synthesis_passes import synthesis_passes

TICKS = """\
2026-09-14 08:00:00 pass start: task --producer task --workers 8
2026-09-14 08:05:00 pass done: task exit 0;  synthesized 3, already present 9, failed conversations 0, deferred 40, registry /private/path
2026-09-14 08:05:01 pass start: local --producer local --model model-a:7b --workers 4 --project /private/dir
2026-09-14 09:00:01 pass done: local exit 124;
2026-09-14 09:15:00 pass start: local --producer local --model model-a:7b --workers 4
2026-09-14 10:15:00 pass start: local --producer local --model model-a:7b --workers 4
2026-09-14 11:10:00 pass done: local exit 137;
task runners rest until somewhere; running the local lane
2026-09-14 11:20:00 pass start: local --producer local --model model-a:7b --workers 4
"""

PASS_OUTPUT = """\
  2 conversations hold uncollected worker results; walking them first
  [1/40] 0123456789ab +2 (skipped 1)
  [2/40] 0123456789ac FAILED: worker job still pending for a private title
  [3/40] 0123456789ad +0 (skipped 4)
"""


def _local(stamp: str) -> str:
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").astimezone().strftime("%H:%M")


def test_passes_carry_exit_state_and_tallies():
    passes = parse_pass_log(TICKS.splitlines())
    assert [entry["state"] for entry in passes] == [
        "ok",
        "timeout",
        "interrupted",
        "killed",
        "running",
    ]
    first, timed_out = passes[0], passes[1]
    assert (first["synthesized"], first["skipped"], first["failed"], first["deferred"]) == (
        3,
        9,
        0,
        40,
    )
    assert first["durationS"] == 300
    assert first["producer"] == "task"
    assert first["model"] is None
    assert timed_out["exitCode"] == 124
    assert timed_out["synthesized"] is None
    assert timed_out["model"] == "model-a:7b"
    assert timed_out["durationS"] == 3300
    assert passes[-1]["finishedAt"] is None


def test_no_path_from_a_log_line_is_published():
    text = json.dumps(parse_pass_log(TICKS.splitlines()))
    assert "/private" not in text


def test_instants_are_utc():
    first = parse_pass_log(TICKS.splitlines())[0]
    assert first["startedAt"].endswith("Z")
    started = datetime.fromisoformat(first["startedAt"]).astimezone()
    assert started.strftime("%H:%M") == _local("2026-09-14 08:00:00")


def test_progress_counts_without_failure_text(tmp_path):
    log = tmp_path / "synthesis-pass.log"
    log.write_text(PASS_OUTPUT)
    progress = pass_progress(log)
    assert progress is not None
    assert {key: progress[key] for key in ("conversations", "finished", "failed")} == {
        "conversations": 40,
        "finished": 2,
        "failed": 1,
    }
    assert progress["synthesized"] == 2
    assert progress["walled"] is False
    assert "private" not in json.dumps(progress)
    assert pass_progress(tmp_path / "absent.log") is None


def test_the_document_names_the_last_pass_and_the_failing_streak(tmp_path):
    (tmp_path / "synthesis.log").write_text(TICKS)
    (tmp_path / "synthesis-pass.log").write_text(PASS_OUTPUT)
    document = synthesis_passes(tmp_path, 0.0, 2)
    assert document["schemaVersion"] == 1
    assert document["lastPass"]["state"] == "running"
    assert document["unsuccessfulStreak"] == 3
    assert document["progress"]["finished"] == 2
    assert [entry["state"] for entry in document["passes"]] == ["running", "killed"]


def test_a_finished_last_pass_has_no_progress(tmp_path):
    (tmp_path / "synthesis.log").write_text("\n".join(TICKS.splitlines()[:4]) + "\n")
    (tmp_path / "synthesis-pass.log").write_text(PASS_OUTPUT)
    document = synthesis_passes(tmp_path, 0.0, 5)
    assert document["lastPass"]["state"] == "timeout"
    assert document["unsuccessfulStreak"] == 1
    assert document["progress"] is None


def test_no_log_is_no_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path))
    assert main(["synthesis", "passes", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["lastPass"] is None
    assert document["passes"] == []
    assert document["unsuccessfulStreak"] == 0
