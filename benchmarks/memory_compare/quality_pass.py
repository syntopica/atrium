"""Measure reranking quality separately from the production deadline."""

import json
import time
from functools import partial
from unittest.mock import patch

import numpy as np
import onnxruntime

from atrium.context.load_dense_matrix import load_dense_matrix
from atrium.context.rerank_populations import rerank_populations
from atrium.rerank.cross_encoder import CrossEncoder
from atrium.store.open_store import open_store
from benchmarks.memory_compare.cached_embedder import CachedEmbedder
from benchmarks.memory_compare.query_backend import query_backend
from benchmarks.memory_compare.score_query import score_query
from benchmarks.memory_compare.single_thread_session import single_thread_session
from benchmarks.memory_compare.source_identity import source_identity
from benchmarks.memory_compare.summarize import summarize
from benchmarks.memory_compare.verify_snapshot import verify_snapshot


def quality_pass(directory):
    """Use the frozen inputs and a disclosed 120-second experimental budget."""
    manifest = json.loads((directory / "manifest.json").read_text())
    documents = verify_snapshot(directory, manifest)
    available = {source_identity(value) for value in documents.values()}
    questions = json.loads((directory / "questions.json").read_text())
    vectors = np.load(directory / "queries.npy", allow_pickle=False)
    matrix = load_dense_matrix(directory / "matrix.npz")
    embedder = CachedEmbedder(
        {}, {row["question"]: vector for row, vector in zip(questions, vectors, strict=True)}
    )
    connection = open_store(directory / "snapshot.sqlite3", read_only=True)
    backends = {
        "matrix": matrix,
        "connection": connection,
        "directory": directory,
        "embedder": embedder,
        "reranker": CrossEncoder(),
    }
    output = []
    factory = single_thread_session(onnxruntime.InferenceSession)
    expanded = partial(rerank_populations, budget_s=120.0)
    with (
        patch.object(onnxruntime, "InferenceSession", factory),
        patch("atrium.context.retrieve_context.rerank_populations", expanded),
        (directory / "quality_results.jsonl").open("x") as handle,
    ):
        for index, question in enumerate(questions):
            started = time.perf_counter()
            error = None
            try:
                ids, warnings = query_backend(
                    "atrium_reranked", question["question"], backends, {}, vectors[index]
                )
            except Exception as failure:
                ids, warnings = [], []
                error = type(failure).__name__
            row = score_query(question, [documents[key] for key in ids], available)
            row.update(
                {
                    "backend": "atrium_quality_120s",
                    "record_ids": ids,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                    "warnings": warnings,
                    "error": error,
                }
            )
            output.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(
                f"quality query {index + 1}/{len(questions)} rank={row['rank']} error={error}",
                flush=True,
            )
    (directory / "quality_summary.json").write_text(json.dumps(summarize(output), indent=2))
    connection.close()
    print("quality pass complete", flush=True)
