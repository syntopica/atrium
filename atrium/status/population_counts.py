"""Per-population registry, intended and indexed counts for a status document."""

from pathlib import Path
from typing import Any

from atrium.forget.forget_ledger_file import forget_ledger_file
from atrium.forget.forgotten_ids import forgotten_ids
from atrium.synthesize.population_report import population_report


def population_counts(
    registry: Path, indexed_episodes: set[str], excluded_conversations: set[str]
) -> list[dict[str, Any]]:
    """Return the `status` population table as counts only, keyed for JSON readers.

    ``records`` and ``episodes`` are what the registry holds, ``intended`` what
    the active recipe would serve, ``indexed`` how many of those the index
    holds; ``intended - indexed`` is the drift `status` prints as NOT IN INDEX.
    ``excluded`` counts episodes of automation the ingest refuses on purpose,
    ``forgotten`` those the forget ledger keeps out.
    """
    return [
        {
            "model": row["model"],
            "listed": row["listed"],
            "records": row["records"],
            "episodes": row["episodes"],
            "intended": row["intended"],
            "indexed": row["indexed"],
            "excluded": row["excluded"],
            "forgotten": row["forgotten"],
        }
        for row in population_report(
            registry, indexed_episodes, excluded_conversations, forgotten_ids(forget_ledger_file())
        )
    ]
