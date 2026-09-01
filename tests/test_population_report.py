"""Every synthesis population is named next to how much of it is served.

The active-recipe manifest silently excluded an entire producer population on
2026-08-30 -- 3,686 episodes already paid for in quota -- and it took an audit
to notice.
"""

import json

from atrium.synthesize.choose_served_records import choose_served_records
from atrium.synthesize.population_report import population_report


def _registry(tmp_path, records):
    directory = tmp_path / "registry" / "records"
    directory.mkdir(parents=True)
    for position, record in enumerate(records):
        (directory / f"job-{position}.json").write_text(json.dumps(record))
    (tmp_path / "registry" / "active-recipe.json").write_text(
        json.dumps({"model_priority": ["codex-cli-default", "claude-sonnet-5"]})
    )
    return tmp_path / "registry"


def test_the_highest_priority_model_wins_a_shared_episode():
    chosen = choose_served_records(
        [
            {"episode_id": "e1", "model_requested": "claude-sonnet-5"},
            {"episode_id": "e1", "model_requested": "codex-cli-default"},
        ],
        ["codex-cli-default", "claude-sonnet-5"],
    )
    assert chosen["e1"]["model_requested"] == "codex-cli-default"


def test_an_unlisted_population_still_serves_what_only_it_covers():
    """Dropping it is how 3,686 paid-for episodes vanished on 2026-08-30."""
    chosen = choose_served_records(
        [{"episode_id": "e9", "model_requested": "gemini-3.7-flash-medium"}],
        ["codex-cli-default"],
    )
    assert chosen["e9"]["model_requested"] == "gemini-3.7-flash-medium"


def test_population_report_counts_records_episodes_and_served(tmp_path):
    registry = _registry(
        tmp_path,
        [
            {"episode_id": "e1", "model_requested": "codex-cli-default"},
            {"episode_id": "e1", "model_requested": "claude-sonnet-5"},
            {"episode_id": "e2", "model_requested": "claude-sonnet-5"},
            {"episode_id": "e2", "model_requested": "gemini-3.7-flash-medium"},
        ],
    )
    rows = {row["model"]: row for row in population_report(registry)}
    assert rows["codex-cli-default"]["served"] == 1
    assert rows["claude-sonnet-5"]["served"] == 1
    # Fully shadowed: every episode it has, a higher-priority model also has.
    assert rows["gemini-3.7-flash-medium"]["served"] == 0
    assert rows["gemini-3.7-flash-medium"]["listed"] is False
    assert rows["claude-sonnet-5"]["records"] == 2
    assert rows["claude-sonnet-5"]["episodes"] == 2


def test_a_machine_without_a_registry_reports_nothing_and_writes_nothing(tmp_path):
    absent = tmp_path / "nowhere"
    assert population_report(absent) == []
    assert not absent.exists(), "a status must never create the registry"
