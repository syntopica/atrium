"""Compute one common set of query embeddings on a single CPU thread."""

import hashlib
import json
import time
from functools import partial
from pathlib import Path
from unittest.mock import patch

import numpy as np
import onnxruntime

from atrium.embed.query_embedder import query_embedder


def freeze_queries(questions: list[dict], directory: Path) -> dict:
    """Persist validated vectors, with embedding latency outside retrieval timing."""
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
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
    factory = partial(onnxruntime.InferenceSession, sess_options=options)
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
