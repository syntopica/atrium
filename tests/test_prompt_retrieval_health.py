"""doctor warns when Claude Code here no longer retrieves context before each prompt."""

import json

from atrium.doctor.prompt_retrieval_health import prompt_retrieval_health


def _write(path, settings):
    path.write_text(json.dumps(settings))
    return path


def test_the_enabled_plugin_is_a_route(tmp_path):
    path = _write(tmp_path / "settings.json", {"enabledPlugins": {"atrium-context@atrium": True}})
    assert prompt_retrieval_health([path]).severity == "ok"


def test_a_prompt_hook_calling_atrium_is_a_route(tmp_path):
    hooks = {"UserPromptSubmit": [{"hooks": [{"command": "bash ~/p/atrium/hooks/prompt.sh"}]}]}
    assert prompt_retrieval_health([_write(tmp_path / "s.json", {"hooks": hooks})]).severity == "ok"


def test_a_dropped_or_disabled_plugin_warns_and_names_the_file(tmp_path):
    dropped = _write(tmp_path / "a.json", {"enabledPlugins": {"caveman@caveman": True}})
    disabled = _write(tmp_path / "b.json", {"enabledPlugins": {"atrium-context@atrium": False}})
    finding = prompt_retrieval_health([dropped, disabled])
    assert finding.severity == "warn"
    assert finding.code == "prompt_retrieval_missing"
    assert finding.detail["settings"] == [str(dropped), str(disabled)]


def test_a_host_without_claude_code_passes(tmp_path):
    assert prompt_retrieval_health([tmp_path / "absent.json"]).severity == "ok"
