"""Dispatch retrieval to the actual backend API with a common output budget."""

import numpy as np

from atrium.context.retrieve_context import retrieve_context


def query_backend(name, question, backends, _records, vector):
    """Return record IDs and runtime diagnostics without answer-label routing."""
    if name == "mem0":
        result = backends["mem0"].search(question, top_k=8, filters={"user_id": "paired-benchmark"})
        return [row["metadata"]["record_id"] for row in result["results"]], []
    if name == "chroma":
        result = backends["chroma"].query(
            query_embeddings=[vector.tolist()], n_results=8, include=["distances"]
        )
        return result["ids"][0], []
    if name == "exact_dense":
        scores = backends["matrix"].vectors @ vector
        order = np.argsort(-scores, kind="stable")[:8]
        return [str(backends["matrix"].ids[index]) for index in order], []
    if name not in {"atrium_reranked", "atrium_fused"}:
        raise ValueError("unknown retrieval backend")
    response = retrieve_context(
        backends["connection"],
        question,
        limit=8,
        max_chars=16000,
        lane="auto",
        embedder=backends["embedder"],
        dense_matrix=backends["matrix"],
        state=backends["directory"],
        reranker=backends["reranker"] if name == "atrium_reranked" else None,
    )
    if response["index_status"] not in {"ready", "empty"}:
        raise RuntimeError("Atrium snapshot was not readable")
    return [row["record_id"] for row in response["evidence"]], response["warnings"]
