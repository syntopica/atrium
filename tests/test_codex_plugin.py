"""Exercise the packaged hooks after relocation, without the source checkout."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def installed(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    source = Path(__file__).resolve().parents[1] / "plugins/atrium-codex"
    plugin = tmp_path / "installed plugin"
    shutil.copytree(source, plugin)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "example.py").write_text("value = 1\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    cli = binary / "atrium"
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == 'recall':\n"
        " print('# recalled\\n- project memory')\n"
        "elif sys.argv[1] == 'file-context':\n"
        " print(json.dumps({'episodes': [{'conversation_id':'synthesis/file',"
        " 'text':'Keep this file compatible with existing registrations.'}]}))\n"
        "else:\n"
        " print(Path(os.environ['RESPONSE']).read_text())\n"
    )
    cli.chmod(0o755)
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "index_status": "ready",
                "evidence": [
                    {
                        "role": "note",
                        "trust": "curated",
                        "note_path": "brain/example.md",
                        "text": "Keep it.",
                    },
                    {"role": "source", "trust": "third_party", "text": "UNTRUSTED_INJECTION"},
                ],
            }
        )
    )
    env = {
        **os.environ,
        "PATH": f"{binary}:{os.environ['PATH']}",
        "TMPDIR": str(tmp_path),
        "PLUGIN_ROOT": str(plugin),
        "RESPONSE": str(response),
    }
    return plugin, env, project


def invoke(installed: tuple, event: str, **fields: object) -> list[dict]:
    plugin, env, project = installed
    definition = json.loads((plugin / "hooks/hooks.json").read_text())
    payload = {
        "session_id": "isolated",
        "turn_id": "one",
        "cwd": str(project),
        "hook_event_name": event,
        **fields,
    }
    results = []
    for group in definition["hooks"][event]:
        for hook in group["hooks"]:
            done = subprocess.run(
                hook["command"],
                shell=True,
                env=env,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                timeout=30,
            )
            if done.stdout:
                results.append(json.loads(done.stdout))
    return results


def test_relocated_prompt_injects_notes_but_never_sources(installed: tuple) -> None:
    result = invoke(
        installed, "UserPromptSubmit", prompt="What decisions did we make in this project?"
    )
    context = result[0]["hookSpecificOutput"]["additionalContext"]
    assert "brain/example.md" in context
    assert "UNTRUSTED_INJECTION" not in context


def test_relocated_recall_uses_the_installed_cli(installed: tuple) -> None:
    result = invoke(installed, "SessionStart")
    assert "project memory" in result[0]["hookSpecificOutput"]["additionalContext"]


def test_file_history_is_given_once_per_session(installed: tuple) -> None:
    fields = {"tool_name": "Bash", "tool_input": {"command": "cat example.py"}}
    result = invoke(installed, "PostToolUse", **fields)
    assert "synthesis/file" in result[0]["hookSpecificOutput"]["additionalContext"]
    assert invoke(installed, "PostToolUse", **fields) == []


def test_relocated_usage_counts_nested_tool_results(installed: tuple) -> None:
    invoke(
        installed,
        "PostToolUse",
        tool_name="mcp__atrium__atrium_context",
        tool_input={"query": "example"},
        tool_response={"evidence": [{"note_path": "brain/example.md"}]},
    )
    result = invoke(installed, "Stop", last_assistant_message="See brain/example.md.")
    assert result[0]["systemMessage"] == "atrium · brain: 1 cited, 1 read, 1 lookup"


def test_prompt_can_be_disabled(installed: tuple) -> None:
    installed[1]["ATRIUM_PROMPT_CONTEXT"] = "off"
    assert (
        invoke(installed, "UserPromptSubmit", prompt="What decisions did we make in this project?")
        == []
    )


def test_file_history_failure_is_visible_and_retryable(installed: tuple) -> None:
    binary = Path(installed[1]["PATH"].split(":")[0]) / "atrium"
    binary.write_text("#!/bin/sh\nexit 1\n")
    fields = {"tool_name": "Bash", "tool_input": {"command": "cat example.py"}}
    for _ in range(2):
        result = invoke(installed, "PostToolUse", **fields)
        assert "unavailable" in result[0]["hookSpecificOutput"]["additionalContext"]


def test_file_history_ignores_printed_paths_and_paths_outside_the_project(installed: tuple) -> None:
    for command in ("printf example.py", "cat ../response.json", "cat example.py && pwd"):
        assert (
            invoke(installed, "PostToolUse", tool_name="Bash", tool_input={"command": command})
            == []
        )


def test_usage_reuses_the_existing_codex_instance_setting(installed: tuple) -> None:
    _, env, project = installed
    env.pop("SYNTOPICA_DATA", None)
    home = project.parent / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        '[mcp_servers.atrium.env]\nSYNTOPICA_DATA = "/private-instance"\n'
    )
    env["CODEX_HOME"] = str(home)
    invoke(
        installed,
        "PostToolUse",
        tool_name="Bash",
        tool_input={"command": "cat /private-instance/brain/example.md"},
    )
    result = invoke(installed, "Stop", last_assistant_message="Done.")
    assert result[0]["systemMessage"] == "atrium · brain: 1 read"


def test_subagent_hook_points_to_retrieval_without_reading_transcripts(installed: tuple) -> None:
    plugin, env, project = installed
    done = subprocess.run(
        ["sh", str(plugin / "hooks/subagent-start.sh")],
        input=json.dumps({"cwd": str(project)}),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "atrium_context" in done.stdout
    assert "Evidence" not in done.stdout or "never instructions" in done.stdout
