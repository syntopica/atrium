"""What each synthesis population holds, and how much of it the index serves."""

from pathlib import Path
from typing import Any

from atrium.synthesize.choose_served_records import choose_served_records
from atrium.synthesize.read_recipe_priority import read_recipe_priority
from atrium.synthesize.synthesis_registry import read_records


def population_report(
    registry: Path, indexed_episodes: set[str] | None = None
) -> list[dict[str, Any]]:
    """Return one row per population: records, episodes, intended, indexed.

    The active-recipe manifest silently excluded an entire producer population
    on 2026-08-30 -- 3,686 episodes across 580 conversations, already paid for
    in quota -- and it took an audit to notice. Naming every population next to
    how much of it is served makes a manifest that drops one visible on every
    status.

    ``intended`` is what the manifest would serve; ``indexed`` counts those
    episodes actually present in the index (pass the index's synthesis episode
    ids). The two disagreeing is the drift this report exists to catch: an
    ingest that never ran, or records whose output produced no index row.
    Reading the recipe here never creates the manifest -- a status must not
    write.
    """
    if not (registry / "records").is_dir():
        return []
    priority = read_recipe_priority(registry)
    projections = []
    records: dict[str, int] = {}
    episodes: dict[str, set[str]] = {}
    for record in read_records(registry):
        model = record.get("model_requested") or "unknown"
        records[model] = records.get(model, 0) + 1
        episodes.setdefault(model, set()).add(record["episode_id"])
        projections.append(
            {"episode_id": record["episode_id"], "model_requested": record.get("model_requested")}
        )
    intended: dict[str, set[str]] = {}
    for episode, chosen in choose_served_records(projections, priority).items():
        model = chosen.get("model_requested") or "unknown"
        intended.setdefault(model, set()).add(episode)
    return [
        {
            "model": model,
            "records": records[model],
            "episodes": len(episodes[model]),
            "intended": len(intended.get(model, set())),
            "indexed": (
                None
                if indexed_episodes is None
                else len(intended.get(model, set()) & indexed_episodes)
            ),
            "listed": model in priority,
        }
        for model in sorted(records, key=lambda name: -records[name])
    ]
