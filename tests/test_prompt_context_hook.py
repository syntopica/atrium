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
    (tmp_path / ".git").mkdir()
    marker = tmp_path / "still-running"
    fake = tmp_path / "atrium"
    fake.write_text(f"#!/bin/sh\n(sleep 20; touch {marker}) &\nwait\n")
    fake.chmod(0o755)
    out = _run(
        {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
        {"ATRIUM_PROMPT_CONTEXT_TIMEOUT": "1"},
        tmp_path,
    )
    assert "atrium context unavailable" in out
    subprocess.run(["sleep", "3"], check=False)
    assert not marker.exists()


def test_a_failed_retrieval_says_so_instead_of_staying_silent(tmp_path: Path) -> None:
    """Silence after a failure reads as "nothing on record", which it is not."""
    (tmp_path / ".git").mkdir()
    fake = tmp_path / "atrium"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o755)
    out = _run(
        {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
        {},
        tmp_path,
    )
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "call `atrium_context`" in context


def _answering(tmp_path: Path, body: dict) -> str:
    (tmp_path / ".git").mkdir()
    fake = tmp_path / "atrium"
    fake.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(body)}\nEOF\n")
    fake.chmod(0o755)
    return _run(
        {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
        {},
        tmp_path,
    )


def test_an_unreadable_index_is_a_failure_not_an_empty_record(tmp_path: Path) -> None:
    """Valid JSON from an index that could not be read still answered nothing."""
    out = _answering(tmp_path, {"index_status": "unavailable", "evidence": []})
    assert "atrium context unavailable" in out


def test_a_read_index_with_no_match_stays_silent(tmp_path: Path) -> None:
    assert _answering(tmp_path, {"index_status": "ready", "evidence": []}) == ""


def test_a_session_outside_any_project_retrieves_over_all_history(tmp_path: Path) -> None:
    """Outside a repository the hook asks without a scope instead of asking nothing."""
    body = {
        "index_status": "ready",
        "evidence": [{"trust": "curated", "note_path": "brain/topics/a.md", "text": "A note."}],
    }
    fake = tmp_path / "atrium"
    fake.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" >'{tmp_path}/argv'\n"
        f"cat <<'EOF'\n{json.dumps(body)}\nEOF\n"
    )
    fake.chmod(0o755)
    out = _run(
        {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
        {},
        tmp_path,
    )
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv[:2] == ["context", "a prompt long enough to reach retrieval"]
    assert "--project" not in argv
    assert "brain/topics/a.md" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_a_session_inside_a_project_keeps_its_scope(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    fake = tmp_path / "atrium"
    fake.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" >'{tmp_path}/argv'\n"
        'echo \'{"index_status": "ready", "evidence": []}\'\n'
    )
    fake.chmod(0o755)
    _run(
        {"prompt": "a prompt long enough to reach retrieval", "cwd": str(tmp_path)},
        {},
        tmp_path,
    )
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv[argv.index("--project") + 1] == str(tmp_path)


def test_a_healthy_retrieval_shows_the_person_no_warning(tmp_path: Path) -> None:
    """Claude Code draws `systemMessage` as a warning, so success carries none."""
    evidence = [
        {"trust": "curated", "text": "a note", "note_path": "brain/a.md"},
        {"trust": "synthesized", "text": "one", "conversation_id": "synthesis/abc"},
        {"trust": "synthesized", "text": "two", "conversation_id": "synthesis/def"},
    ]
    out = json.loads(_answering(tmp_path, {"index_status": "ready", "evidence": evidence}))
    assert "systemMessage" not in out
    assert "a note" in out["hookSpecificOutput"]["additionalContext"]


def test_a_failure_is_shown_to_the_person_too(tmp_path: Path) -> None:
    out = json.loads(_answering(tmp_path, {"index_status": "unavailable", "evidence": []}))
    assert out["systemMessage"] == "atrium: index not readable (unavailable)"
