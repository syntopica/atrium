"""The UserPromptSubmit hook's renderer: what it skips, and what it leaves behind."""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks/claude-code/user_prompt_context.py"


def _run(payload: dict, environment: dict[str, str], path_dir: Path | None = None) -> str:
    env = {"PATH": f"{path_dir}:/usr/bin:/bin" if path_dir else "/usr/bin:/bin", **environment}
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_a_short_prompt_is_not_worth_a_retrieval(tmp_path: Path) -> None:
    assert _run({"prompt": "hi", "cwd": str(tmp_path)}, {}) == ""


def test_a_slash_command_is_not_a_question(tmp_path: Path) -> None:
    assert (
        _run({"prompt": "/commit the work that is staged right now", "cwd": str(tmp_path)}, {})
        == ""
    )


def test_a_timeout_leaves_no_retrieval_running(tmp_path: Path) -> None:
    """`subprocess.run`'s timeout kills the child it started, not the tree."""
    marker = tmp_path / "still-running"
    fake = tmp_path / "atrium"
    fake.write_text(f"#!/bin/sh\n(sleep 20; touch {marker}) &\nwait\n")
    fake.chmod(0o755)
    assert (
        _run(
            {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
            {"ATRIUM_PROMPT_CONTEXT_TIMEOUT": "1"},
            tmp_path,
        )
        == ""
    )
    subprocess.run(["sleep", "3"], check=False)
    assert not marker.exists()
