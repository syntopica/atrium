"""The `curate-screen` command: stage one of the promotion pipeline."""

from pathlib import Path

from atrium.curate.curation_directory import curation_directory
from atrium.curate.screen_registry import screen_registry
from atrium.curate.write_ledger import write_ledger


def run_curate_screen_cli(registry: Path) -> int:
    """Screen the registry into a candidate ledger and report what it did."""
    report = screen_registry(registry)
    directory = curation_directory()
    written = write_ledger(directory, report)
    repeated = sum(1 for candidate in report.candidates if len(candidate.sources) > 1)
    print(f"  {report.records:,} records, {report.facts:,} facts")
    print(f"  {len(report.candidates):,} distinct candidates ({repeated:,} stated more than once)")
    print(f"  {len(report.quarantined):,} quarantined")
    for reason, count in report.reasons.items():
        print(f"    {reason:24} {count:,}")
    print(f"  ledger {written['candidates']}")
    print(f"  quarantine {written['quarantine']}")
    return 0
