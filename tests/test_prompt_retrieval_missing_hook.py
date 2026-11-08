"""The session-start helper names a Claude Code profile that lost per-prompt retrieval."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "hooks" / "claude-code" / "prompt_retrieval_missing.py"
)


def run_in(profile: Path) -> str:
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(profile)}
    return subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_names_settings_without_the_plugin(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(json.dumps({"enabledPlugins": {}}))
    assert run_in(tmp_path) == str(tmp_path / "settings.json")


def test_silent_when_the_plugin_is_enabled(tmp_path: Path) -> None:
    settings = {"enabledPlugins": {"atrium-context@atrium": True}}
    (tmp_path / "settings.json").write_text(json.dumps(settings))
    assert run_in(tmp_path) == ""


def test_silent_when_settings_are_unreadable(tmp_path: Path) -> None:
    assert run_in(tmp_path) == ""
