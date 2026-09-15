"""State follows the instance: the index sits beside the config that owns it.

Before instances existed the index lived at `~/.atrium`, invisible to the
doctor of the data directory it served. Now the data directory decides.
"""

import json
from pathlib import Path

from atrium.state.state_directory import state_directory


def _instance(root: Path, config: dict[str, object] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "syntopica.config.json").write_text(json.dumps(config or {}))
    return root


def test_the_explicit_override_wins(tmp_path: Path):
    _instance(tmp_path / "wiki")
    env = {"ATRIUM_STATE": str(tmp_path / "elsewhere"), "SYNTOPICA_DATA": str(tmp_path / "wiki")}
    assert state_directory(env, cwd=tmp_path) == tmp_path / "elsewhere"


def test_the_selected_instance_defaults_to_its_atrium_directory(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki")
    assert state_directory({"SYNTOPICA_DATA": str(wiki)}, cwd=tmp_path) == wiki / "atrium"


def test_a_declared_path_resolves_against_the_file_that_declared_it(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki", {"atrium": {"path": "state/atrium"}})
    assert state_directory({"SYNTOPICA_DATA": str(wiki)}, cwd=tmp_path) == wiki / "state/atrium"


def test_the_local_file_outranks_the_tracked_one(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki", {"atrium": {"path": "tracked"}})
    (wiki / "syntopica.local.json").write_text(json.dumps({"atrium": {"path": "/abs/local"}}))
    assert state_directory({"SYNTOPICA_DATA": str(wiki)}, cwd=tmp_path) == Path("/abs/local")


def test_the_enclosing_instance_is_found_from_a_subdirectory(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki")
    (wiki / ".git").mkdir()
    deep = wiki / "brain" / "projects"
    deep.mkdir(parents=True)
    assert state_directory({}, cwd=deep) == wiki / "atrium"


def test_another_repository_stops_the_walk(tmp_path: Path):
    wiki = _instance(tmp_path / "wiki")
    other = wiki / "checkouts" / "engine"
    other.mkdir(parents=True)
    (other / ".git").mkdir()
    assert state_directory({}, cwd=other, home=tmp_path / "home") == tmp_path / "home" / ".atrium"


def test_no_instance_falls_back_to_the_home_directory(tmp_path: Path):
    lone = tmp_path / "lone"
    lone.mkdir()
    (lone / ".git").mkdir()
    assert state_directory({}, cwd=lone, home=tmp_path / "home") == tmp_path / "home" / ".atrium"


def test_an_unreadable_config_still_yields_the_default(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "syntopica.config.json").write_text("{not json")
    assert state_directory({"SYNTOPICA_DATA": str(wiki)}, cwd=tmp_path) == wiki / "atrium"
