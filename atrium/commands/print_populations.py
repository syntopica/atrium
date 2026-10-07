"""The per-population synthesis summary `status` prints."""

from pathlib import Path

from atrium.synthesize.default_registry import default_registry


def print_populations(registry: Path | None, indexed_episodes: set[str]) -> None:
    """Name every synthesis population and how much of it the index serves.

    The active-recipe manifest silently excluded an entire producer population
    on 2026-08-30, and it took an audit to notice. Two numbers per population:
    what the manifest intends to serve, and how many of those episodes the
    index actually holds -- they disagree exactly when an ingest never ran or a
    record's output produced no index row, which is the drift worth catching.
    """
    from atrium.synthesize.population_report import population_report

    rows = population_report(
        registry if registry is not None else default_registry(), indexed_episodes
    )
    if not rows:
        return
    print("  synthesis populations (registry -> intended -> in index):")
    for row in rows:
        unlisted = "" if row["listed"] else "  (not in active recipe)"
        missing = row["intended"] - row["indexed"]
        drift = f"  <- {missing:,} NOT IN INDEX" if missing else ""
        dropped = "  <- SERVES NOTHING" if row["intended"] == 0 else ""
        print(
            f"    {row['model']:<26} {row['records']:>7,} records "
            f"{row['episodes']:>7,} episodes {row['intended']:>7,} intended "
            f"{row['indexed']:>7,} indexed{unlisted}{dropped}{drift}"
        )
