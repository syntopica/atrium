"""Interleave backend calls to avoid assigning one system a different load window."""

import json
import random
import time

from benchmarks.memory_compare.query_backend import query_backend
from benchmarks.memory_compare.score_query import score_query
from benchmarks.memory_compare.source_identity import source_identity


def run_queries(questions, corpus, vectors, backends, output):
    """Keep errors in the denominator and every completed result in a journal."""
    records = {row["record_id"]: row for row in corpus}
    available = {source_identity(row["conversation_id"]) for row in corpus}
    names = ["atrium_reranked", "atrium_fused", "mem0", "chroma", "exact_dense"]
    rng = random.Random(20261021)
    results = {name: [] for name in names}
    with output.open("x") as handle:
        for index, question in enumerate(questions):
            order = rng.sample(names, len(names))
            for name in order:
                started = time.perf_counter()
                error = None
                try:
                    ids, warnings = query_backend(
                        name, question["question"], backends, records, vectors[index]
                    )
                except Exception as failure:
                    ids, warnings = [], []
                    error = type(failure).__name__
                row = score_query(
                    question, [records[key]["conversation_id"] for key in ids], available
                )
                row.update(
                    {
                        "backend": name,
                        "elapsed_ms": (time.perf_counter() - started) * 1000,
                        "record_ids": ids,
                        "warnings": warnings,
                        "error": error,
                    }
                )
                results[name].append(row)
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                print(
                    f"query {index + 1}/{len(questions)} {name} rank={row['rank']} error={error}",
                    flush=True,
                )
    return results
