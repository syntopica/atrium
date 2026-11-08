"""Recompute every ranking score and aggregate from the private result journal."""

import json
from collections import defaultdict

from benchmarks.memory_compare.paired_differences import paired_differences
from benchmarks.memory_compare.score_query import score_query
from benchmarks.memory_compare.source_identity import source_identity
from benchmarks.memory_compare.summarize import summarize


def verify_results(directory, documents):
    """Reject missing questions, duplicate calls and unearned answer credit."""
    queries = json.loads((directory / "questions.json").read_text())
    questions = {(row["split"], row["id"]): row for row in queries}
    available = {source_identity(value) for value in documents.values()}
    results = defaultdict(list)
    for line in (directory / "results.jsonl").read_text().splitlines():
        row = json.loads(line)
        expected = score_query(
            questions[row["split"], row["id"]],
            [documents[key] for key in row["record_ids"]],
            available,
        )
        if any(row[key] != value for key, value in expected.items()):
            raise ValueError("stored query score differs from source-level labels")
        results[row["backend"]].append(row)
    expected_backends = {"atrium_reranked", "atrium_fused", "exact_dense", "mem0", "chroma"}
    if results.keys() != expected_backends:
        raise ValueError("missing backend")
    for rows in results.values():
        keys = [(row["split"], row["id"]) for row in rows]
        if len(keys) != len(questions) or set(keys) != questions.keys():
            raise ValueError("missing or duplicated query result")
    summary = {name: summarize(rows) for name, rows in results.items()}
    if summary != json.loads((directory / "summary.json").read_text()):
        raise ValueError("summary differs from journal")
    if paired_differences(results) != json.loads((directory / "paired.json").read_text()):
        raise ValueError("paired statistics differ from journal")
    return len(questions), sum(map(len, results.values()))
