"""Run the frozen local retrieval experiment without touching the live index."""

import hashlib
import importlib.metadata
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import numpy as np
import onnxruntime

from atrium.context.load_dense_matrix import load_dense_matrix
from atrium.rerank.cross_encoder import CrossEncoder
from atrium.store.open_store import open_store
from benchmarks.memory_compare.cached_embedder import CachedEmbedder
from benchmarks.memory_compare.freeze_queries import freeze_queries
from benchmarks.memory_compare.ingest_backends import ingest_backends
from benchmarks.memory_compare.load_questions import load_questions
from benchmarks.memory_compare.paired_differences import paired_differences
from benchmarks.memory_compare.prepare_snapshot import prepare_snapshot
from benchmarks.memory_compare.run_queries import run_queries
from benchmarks.memory_compare.summarize import summarize


def execute(index: Path, evaluations: Path, directory: Path) -> None:
    """Freeze corpus before reading labels, then build and score all backends."""
    if (directory / "results.jsonl").exists():
        raise FileExistsError("preserve completed or partial results; use a new output directory")
    snapshot_manifest = directory / "snapshot_manifest.json"
    if snapshot_manifest.exists():
        manifest = json.loads(snapshot_manifest.read_text())
    else:
        manifest = prepare_snapshot(index, directory)
        snapshot_manifest.write_text(json.dumps(manifest, indent=2))
    questions = load_questions(evaluations, directory)
    manifest.update(freeze_queries(questions, directory))
    matrix = load_dense_matrix(directory / "matrix.npz")
    if matrix is None:
        raise ValueError("snapshot matrix failed validation")
    corpus = [json.loads(line) for line in (directory / "corpus.jsonl").read_text().splitlines()]
    query_vectors = np.load(directory / "queries.npy", allow_pickle=False)
    by_id = {str(key): value for key, value in zip(matrix.ids, matrix.vectors, strict=True)}
    embedder = CachedEmbedder(
        {row["text"]: by_id[row["record_id"]] for row in corpus},
        {row["question"]: vector for row, vector in zip(questions, query_vectors, strict=True)},
    )
    memory, chroma, timings = ingest_backends(directory, corpus, matrix, embedder)
    manifest.update(timings)
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    backends = {
        "mem0": memory,
        "chroma": chroma,
        "matrix": matrix,
        "embedder": embedder,
        "directory": directory,
        "connection": open_store(directory / "snapshot.sqlite3", read_only=True),
        "reranker": CrossEncoder(),
    }
    factory = partial(onnxruntime.InferenceSession, sess_options=options)
    with patch.object(onnxruntime, "InferenceSession", factory):
        results = run_queries(
            questions, corpus, query_vectors, backends, directory / "results.jsonl"
        )
    manifest["versions"] = {
        name: importlib.metadata.version(name)
        for name in ("mem0ai", "chromadb", "qdrant-client", "fastembed", "onnxruntime")
    }
    manifest["protocol"] = {
        "k": 8,
        "scope": "one shared global corpus",
        "inference": False,
        "network": "blocked",
        "seed": 20261021,
    }
    manifest["hashes"] = {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in ("questions.json", "queries.npy")
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (directory / "summary.json").write_text(
        json.dumps({name: summarize(rows) for name, rows in results.items()}, indent=2)
    )
    (directory / "paired.json").write_text(json.dumps(paired_differences(results), indent=2))
    backends["connection"].close()
    print("experiment complete", flush=True)
