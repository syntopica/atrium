"""Derive statistics from an already completed, immutable result journal."""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from benchmarks.memory_compare.breakdown import breakdown
from benchmarks.memory_compare.paired_differences import paired_differences
from benchmarks.memory_compare.quality_comparison import quality_comparison
from benchmarks.memory_compare.summarize import summarize


def main() -> None:
    """Allow independent scoring and verification without re-running retrieval."""
    directory = Path(sys.argv[1])
    results = defaultdict(list)
    for line in (directory / "results.jsonl").read_text().splitlines():
        row = json.loads(line)
        results[row["backend"]].append(row)
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["hashes"] = {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in ("questions.json", "queries.npy")
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (directory / "summary.json").write_text(
        json.dumps({name: summarize(rows) for name, rows in results.items()}, indent=2)
    )
    (directory / "paired.json").write_text(json.dumps(paired_differences(results), indent=2))
    (directory / "breakdown.json").write_text(json.dumps(breakdown(results), indent=2))
    if (directory / "quality_results.jsonl").exists():
        quality = [
            json.loads(line)
            for line in (directory / "quality_results.jsonl").read_text().splitlines()
        ]
        (directory / "quality_summary.json").write_text(json.dumps(summarize(quality), indent=2))
        (directory / "quality_paired.json").write_text(
            json.dumps(quality_comparison(results, quality), indent=2)
        )
        (directory / "quality_breakdown.json").write_text(
            json.dumps(breakdown({"atrium_quality_120s": quality}), indent=2)
        )
    print("statistics recomputed from the completed result journal")


if __name__ == "__main__":
    main()
