"""Verify private corpus parity, complete paired runs and recomputed aggregates."""

import hashlib
import json
import sys
from pathlib import Path

from benchmarks.memory_compare.verify_quality import verify_quality
from benchmarks.memory_compare.verify_results import verify_results
from benchmarks.memory_compare.verify_snapshot import verify_snapshot


def main() -> None:
    """Fail closed on modified inputs, missing results or inconsistent scores."""
    directory = Path(sys.argv[1])
    manifest = json.loads((directory / "manifest.json").read_text())
    documents = verify_snapshot(directory, manifest)
    questions, calls = verify_results(directory, documents)
    if (directory / "quality_results.jsonl").exists():
        calls += verify_quality(directory, documents)
    for name in ("questions.json", "queries.npy"):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != manifest["hashes"][name]:
            raise ValueError("query inputs changed")
    print(
        f"verified {len(documents)} shared records, {questions} questions, {calls} paired results"
    )


if __name__ == "__main__":
    main()
