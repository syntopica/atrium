"""The archive is read from the instance that owns it, not from the home directory."""

import json
from pathlib import Path

from atrium.state.archive_path import archive_path


def _instance(root: Path, config: dict[str, object] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "syntopica.config.json").write_text(json.dumps(config or {}))
    return root


def test_the_selected_instance_defaults_to_its_conversations_directory(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki")
    env = {"SYNTOPICA_DATA": str(wiki)}
    assert archive_path(env, cwd=tmp_path) == wiki / "conversations" / "archive.jsonl"


def test_a_declared_path_is_honoured(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki", {"conversations": {"path": "data/conv"}})
    env = {"SYNTOPICA_DATA": str(wiki)}
    assert archive_path(env, cwd=tmp_path) == wiki / "data/conv" / "archive.jsonl"


def test_the_enclosing_instance_is_used_without_the_variable(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki")
    deep = wiki / "brain"
    deep.mkdir()
    assert archive_path({}, cwd=deep) == wiki / "conversations" / "archive.jsonl"


def test_no_instance_falls_back_to_the_pre_instance_home_path(tmp_path: Path):
    lone = tmp_path / "lone"
    lone.mkdir()
    (lone / ".git").mkdir()
    expected = tmp_path / "home" / ".local/share/rocket-agents/conversations/archive.jsonl"
    assert archive_path({}, cwd=lone, home=tmp_path / "home") == expected
