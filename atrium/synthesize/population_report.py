"""What each synthesis population holds, and how much of it the index serves."""

from pathlib import Path

from atrium.synthesize.active_recipe import active_recipe_priority
from atrium.synthesize.choose_served_records import choose_served_records
from atrium.synthesize.synthesis_registry import read_records


def population_report(registry: Path) -> list[dict]:
    """Return one row per population: records, episodes, episodes served.

    The active-recipe manifest silently excluded an entire producer population
    on 2026-08-30 -- 3,686 episodes across 580 conversations, already paid for
    in quota -- and it took an audit to notice. Naming every population next to
    how much of it is served makes a manifest that drops one visible on every
    status.
    """
    if not (registry / "records").is_dir():
        # No registry on this machine. Returning empty instead of asking the
        # recipe first also keeps this read-only: the manifest is created on
        # first use, and a status must not write anything.
        return []
    priority = active_recipe_priority(registry)
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
    served: dict[str, int] = {}
    for chosen in choose_served_records(projections, priority).values():
        model = chosen.get("model_requested") or "unknown"
        served[model] = served.get(model, 0) + 1
    return [
        {
            "model": model,
            "records": records[model],
            "episodes": len(episodes[model]),
            "served": served.get(model, 0),
            "listed": model in priority,
        }
        for model in sorted(records, key=lambda name: -records[name])
    ]
