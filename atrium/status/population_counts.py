"""Per-population registry, intended and indexed counts for a status document."""

from pathlib import Path
from typing import Any

from atrium.synthesize.population_report import population_report


def population_counts(registry: Path, indexed_episodes: set[str]) -> list[dict[str, Any]]:
    """Return the `status` population table as counts only, keyed for JSON readers.

    ``records`` and ``episodes`` are what the registry holds, ``intended`` what
    the active recipe would serve, ``indexed`` how many of those the index
    holds; ``intended - indexed`` is the drift `status` prints as NOT IN INDEX.
    """
    return [
        {
            "model": row["model"],
            "listed": row["listed"],
            "records": row["records"],
            "episodes": row["episodes"],
            "intended": row["intended"],
            "indexed": row["indexed"],
        }
        for row in population_report(registry, indexed_episodes)
    ]
