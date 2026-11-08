"""Verify common-corpus identity independently of any backend ranking."""

import hashlib
import json

from atrium.context.load_dense_matrix import load_dense_matrix
from atrium.session.redact_sensitive_text import redact_sensitive_text


def verify_snapshot(directory, manifest):
    """Verify frozen text/vector identity and acknowledged backend counts."""
    matrix = load_dense_matrix(directory / "matrix.npz")
    if matrix is None:
        raise ValueError("invalid matrix")
    documents = {}
    digest = hashlib.sha256()
    vectors = {str(key): value for key, value in zip(matrix.ids, matrix.vectors, strict=True)}
    for line in (directory / "corpus.jsonl").read_text().splitlines(keepends=True):
        row = json.loads(line)
        if redact_sensitive_text(row["text"]) != row["text"]:
            raise ValueError("frozen corpus contains a record requiring redaction")
        if row["role"] not in {"note", "synthesis"} or row["record_id"] in documents:
            raise ValueError("ineligible or duplicated corpus record")
        digest.update(line.encode())
        digest.update(vectors[row["record_id"]].tobytes())
        documents[row["record_id"]] = row["conversation_id"]
    if digest.hexdigest() != manifest["corpus_vector_sha256"]:
        raise ValueError("corpus or vector digest changed")
    if not (
        len(documents)
        == len(vectors)
        == manifest["records"]
        == manifest["mem0_records"]
        == manifest["chroma_records"]
    ):
        raise ValueError("corpus parity failed")
    return documents
