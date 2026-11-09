"""Compute one common set of query embeddings on a single CPU thread."""

import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import onnxruntime

from atrium.embed.query_embedder import query_embedder
from benchmarks.memory_compare.single_thread_session import single_thread_session


def freeze_queries(questions: list[dict], directory: Path) -> dict:
    """Persist validated vectors, with embedding latency outside retrieval timing."""
    result = []
    identity = hashlib.sha256(
        json.dumps([row["question"] for row in questions]).encode()
    ).hexdigest()
    cached = directory / "queries_identity.txt"
    if cached.exists() and cached.read_text() == identity:
        return {
            "query_vectors": len(questions),
            "query_dimensions": 384,
            "query_embedding_seconds": None,
            "query_embeddings_reused": True,
        }
    started = time.perf_counter()
    factory = single_thread_session(onnxruntime.InferenceSession)
    with patch.object(onnxruntime, "InferenceSession", factory):
        embedder = query_embedder()
        for index, row in enumerate(questions):
            result.append(embedder.embed([row["question"]])[0])
            print(f"query vector {index + 1}/{len(questions)}", flush=True)
    vectors = np.asarray(result, dtype=np.float32)
    np.save(directory / "queries.npy", vectors, allow_pickle=False)
    cached.write_text(identity)
    return {
        "query_embedding_seconds": time.perf_counter() - started,
        "query_vectors": len(vectors),
        "query_dimensions": int(vectors.shape[1]),
    }
