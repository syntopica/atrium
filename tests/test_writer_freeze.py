"""A frozen writer set must be named, not inferred from an aging archive."""

import os
from pathlib import Path

from atrium.doctor.refresh_health import BROKEN_AFTER_SECONDS
from atrium.doctor.writer_freeze import writer_freeze
from atrium.state.freeze_sentinel_path import freeze_sentinel_path


def _sentinel(tmp_path: Path, age: float, now: float) -> Path:
    sentinel = tmp_path / "migration.freeze"
    sentinel.write_text("frozen\n")
    os.utime(sentinel, (now - age, now - age))
    return sentinel


def test_no_sentinel_is_healthy(tmp_path: Path):
    finding = writer_freeze(tmp_path / "migration.freeze")
    assert (finding.severity, finding.code) == ("ok", "writers_unfrozen")


def test_a_young_freeze_warns_and_names_the_sentinel(tmp_path: Path):
    now = 2_000_000_000.0
    sentinel = _sentinel(tmp_path, 600, now)
    finding = writer_freeze(sentinel, now)
    assert (finding.severity, finding.code) == ("warn", "writers_frozen")
    assert str(sentinel) in finding.summary
    assert finding.detail["age_seconds"] == 600


def test_a_freeze_older_than_a_dead_refresh_is_broken(tmp_path: Path):
    now = 2_000_000_000.0
    finding = writer_freeze(_sentinel(tmp_path, BROKEN_AFTER_SECONDS + 1, now), now)
    assert (finding.severity, finding.code) == ("broken", "writers_frozen_abandoned")


def test_the_sentinel_follows_the_writers_state_variable(tmp_path: Path):
    env = {"ROCKET_AGENTS_CONVERSATION_STATE": str(tmp_path / "state")}
    assert freeze_sentinel_path(env) == tmp_path / "state" / "migration.freeze"


def test_an_empty_or_relative_variable_falls_back_to_the_home_default(tmp_path: Path):
    expected = tmp_path / ".local/state/rocket-agents/conversations/migration.freeze"
    for value in ("", "relative/state"):
        env = {"ROCKET_AGENTS_CONVERSATION_STATE": value}
        assert freeze_sentinel_path(env, home=tmp_path) == expected
