"""The Codex brain-use hook: what it counts, and what it says at the end of a turn."""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks/codex/brain_use.py"
DATA = "/data/wiki"


def _run(payload: dict, tmp_path: Path) -> str:
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path), "SYNTOPICA_DATA": DATA}
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"session_id": "s-1", "turn_id": "t-1", **payload}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _tool(tmp_path: Path, tool: str, tool_input: dict, response: object = "") -> None:
    payload = {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": tool_input}
    assert _run({**payload, "tool_response": response}, tmp_path) == ""


def _stop(tmp_path: Path, answer: str) -> str:
    out = _run({"hook_event_name": "Stop", "last_assistant_message": answer}, tmp_path)
    return json.loads(out)["systemMessage"] if out else ""


def test_a_turn_that_used_nothing_says_nothing(tmp_path: Path) -> None:
    _tool(tmp_path, "Bash", {"command": "ls brain"})
    assert _stop(tmp_path, "Done.") == ""


def test_counts_lookups_reads_and_citations(tmp_path: Path) -> None:
    evidence = json.dumps(
        {"evidence": [{"note_path": "brain/people/ana.md"}], "text": "brain/q.md"}
    )
    _tool(tmp_path, "mcp__atrium__atrium_context", {"query": "ana"}, evidence)
    _tool(tmp_path, "Bash", {"command": "atrium search ana --project ."}, {"stdout": evidence})
    _tool(tmp_path, "mcp__plugin_my_tools_atrium__atrium_search", {"query": "x"}, "")
    _tool(tmp_path, "Bash", {"command": f"cat {DATA}/brain/../secret.md"})
    _tool(tmp_path, "Bash", {"command": f"printf {DATA}/brain/topics/printed.md"})
    _tool(tmp_path, "Bash", {"command": f"sed -n 1,40p {DATA}/brain/topics/x.md"})
    _tool(tmp_path, "Bash", {"command": "cat /work/repo/brain/README.md"})
    notice = _stop(tmp_path, "Per brain/people/ana.md, cited as brain/...md, yes.")
    assert notice == "atrium · brain: 1 cited, 2 read, 3 lookups"


def test_each_turn_keeps_its_own_count(tmp_path: Path) -> None:
    payload = {"hook_event_name": "PostToolUse", "tool_name": "mcp__atrium__atrium_search"}
    _run({**payload, "turn_id": "t-0", "tool_input": {}, "tool_response": ""}, tmp_path)
    assert _stop(tmp_path, "No notes here.") == ""


def test_parallel_tool_calls_all_count(tmp_path: Path) -> None:
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path), "SYNTOPICA_DATA": DATA}
    payload = {"session_id": "s-1", "turn_id": "t-1", "hook_event_name": "PostToolUse"}
    calls = [
        subprocess.Popen([sys.executable, str(HOOK)], stdin=subprocess.PIPE, env=env, text=True)
        for _ in range(8)
    ]
    for index, call in enumerate(calls):
        body = {**payload, "tool_name": "mcp__atrium__atrium_search", "tool_input": {}}
        body["tool_response"] = json.dumps({"note_path": f"brain/n{index}.md"})
        call.stdin.write(json.dumps(body))
        call.stdin.close()
    for call in calls:
        call.wait(timeout=30)
    assert _stop(tmp_path, "") == "atrium · brain: 8 read, 8 lookups"


def test_stop_clears_the_tally(tmp_path: Path) -> None:
    _tool(tmp_path, "mcp__atrium__atrium_recall", {})
    assert _stop(tmp_path, "") == "atrium · brain: 1 lookup"
    assert _stop(tmp_path, "") == ""


def test_bad_input_never_breaks_the_turn(tmp_path: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, check=False
    )
    assert done.returncode == 0
    assert done.stdout == ""


def test_a_planted_link_is_never_written_through(tmp_path: Path) -> None:
    """A shared temporary directory must not let another user redirect the tally."""
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    (tmp_path / f"atrium-brain-use-{os.getuid()}").symlink_to(tmp_path / "elsewhere")
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / ".lock").symlink_to(victim)
    _tool(tmp_path, "mcp__atrium__atrium_search", {"query": "x"})
    assert victim.read_text() == "keep"
    assert not (tmp_path / "elsewhere" / "s-1-t-1.json").exists()
