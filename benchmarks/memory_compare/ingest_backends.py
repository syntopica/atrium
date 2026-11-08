"""Ingest exactly the same frozen records through each backend's native API."""

import time

import chromadb
from chromadb.config import Settings

from benchmarks.memory_compare.make_mem0 import make_mem0


def ingest_backends(directory, corpus, matrix, embedder):
    """Retain native IDs and verify that no record was silently dropped."""
    client = chromadb.EphemeralClient(Settings(anonymized_telemetry=False))
    chroma = client.create_collection(
        "paired_memory",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine", "num_threads": 1}},
    )
    vectors = {str(key): vector for key, vector in zip(matrix.ids, matrix.vectors, strict=True)}
    started = time.perf_counter()
    for start in range(0, len(corpus), 1000):
        batch = corpus[start : start + 1000]
        chroma.add(
            ids=[row["record_id"] for row in batch],
            embeddings=[vectors[row["record_id"]].tolist() for row in batch],
            documents=[row["text"] for row in batch],
        )
        print(f"chroma ingest {start + len(batch)}/{len(corpus)}", flush=True)
    chroma_seconds = time.perf_counter() - started
    if chroma.count() != len(corpus):
        raise ValueError("Chroma corpus parity failed")
    memory = make_mem0(directory, embedder)
    started = time.perf_counter()
    for index, row in enumerate(corpus):
        response = memory.add(
            row["text"],
            user_id="paired-benchmark",
            infer=False,
            metadata={"record_id": row["record_id"]},
        )
        if len(response.get("results", [])) != 1:
            raise ValueError("Mem0 did not acknowledge exactly one input record")
        if (index + 1) % 100 == 0:
            print(f"mem0 ingest {index + 1}/{len(corpus)}", flush=True)
    stored = memory.vector_store.client.count(
        collection_name=memory.collection_name, exact=True
    ).count
    if stored != len(corpus):
        raise ValueError("Mem0 corpus parity failed")
    return (
        memory,
        chroma,
        {
            "chroma_ingest_seconds": chroma_seconds,
            "mem0_ingest_seconds": time.perf_counter() - started,
            "chroma_records": chroma.count(),
            "mem0_records": stored,
        },
    )
