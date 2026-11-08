"""Verify the separate expanded-budget pass against the same frozen labels."""

import json

from benchmarks.memory_compare.score_query import score_query
from benchmarks.memory_compare.source_identity import source_identity
from benchmarks.memory_compare.summarize import summarize


def verify_quality(directory, documents):
    """Require every question exactly once and independently recompute scores."""
    questions = {
        (row["split"], row["id"]): row
        for row in json.loads((directory / "questions.json").read_text())
    }
    available = {source_identity(value) for value in documents.values()}
    rows = [
        json.loads(line) for line in (directory / "quality_results.jsonl").read_text().splitlines()
    ]
    keys = [(row["split"], row["id"]) for row in rows]
    if len(keys) != len(questions) or set(keys) != questions.keys():
        raise ValueError("missing or duplicated quality-pass result")
    for row in rows:
        expected = score_query(
            questions[row["split"], row["id"]],
            [documents[key] for key in row["record_ids"]],
            available,
        )
        if any(row[key] != value for key, value in expected.items()):
            raise ValueError("quality-pass score differs from labels")
    if summarize(rows) != json.loads((directory / "quality_summary.json").read_text()):
        raise ValueError("quality summary differs from its journal")
    return len(rows)
