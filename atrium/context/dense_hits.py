"""Semantic retrieval narrowed by role and workspace before ranking."""

import sqlite3

import numpy as np

from atrium.context.context_scope import context_scope
from atrium.retrieve.hit import Hit


def dense_hits(
    connection: sqlite3.Connection,
    vector: np.ndarray,
    limit: int,
    *,
    curated: bool,
    workspace: str | None = None,
) -> list[Hit]:
    """Rank only indexed role=note vectors, using the existing cosine method."""
    scope, parameters = context_scope(curated, workspace)
    rows = connection.execute(
        "SELECT r.record_id, r.text, r.conversation_id, r.source_sha256, r.authored_at, r.provider, r.role, v.vector FROM records r JOIN vectors v ON v.record_id = r.record_id WHERE 1 = 1"  # noqa: S608 -- fixed SQL fragments; all data is bound
        + scope
        + " ORDER BY r.record_id",
        parameters,
    ).fetchall()
    if not rows:
        return []
    matrix = np.frombuffer(b"".join(row[7] for row in rows), dtype=np.float32).reshape(
        len(rows), -1
    )
    scores = matrix @ np.asarray(vector, dtype=np.float32)
    if not np.isfinite(scores).all():
        raise ValueError("invalid context vector scores")
    return [
        Hit(
            rows[i][0],
            rows[i][1],
            float(scores[i]),
            "dense",
            rows[i][2],
            rows[i][3],
            rows[i][4],
            rows[i][5],
            rows[i][6],
        )
        for i in np.argsort(-scores, kind="stable")[:limit]
    ]
