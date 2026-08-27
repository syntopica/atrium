"""Dense semantic retrieval -- the lane that works when no word overlaps."""

import sqlite3

import numpy as np

from atrium.retrieve.hit import Hit

_QUERY = """
SELECT v.record_id, v.vector, r.text, r.conversation_id, r.source_sha256,
       r.authored_at, r.provider
FROM vectors v
JOIN records r ON r.record_id = v.record_id
ORDER BY v.record_id
"""


def search_dense(
    connection: sqlite3.Connection, query_vector: np.ndarray, limit: int = 20
) -> list[Hit]:
    """Return the records whose vectors are nearest to ``query_vector``.

    Brute-force cosine over every stored vector, deliberately: the semantic
    layer is ~34k vectors and a full scan measures 1.15 ms p50. An approximate
    index would buy nothing here and reintroduce the corruption class the
    previous system paid for (HNSW compaction failures, index divergence).
    """
    rows = connection.execute(_QUERY).fetchall()
    if not rows:
        return []
    matrix = np.frombuffer(b"".join(row[1] for row in rows), dtype=np.float32).reshape(
        len(rows), -1
    )
    scores = matrix @ np.asarray(query_vector, dtype=np.float32)
    # Ties break on record_id (the rows arrive record_id-ordered and the sort
    # is stable), never on physical row order: a fresh build and a reconciled
    # build store identical rows in different order, and equal-score results
    # must still rank identically on every machine.
    order = np.argsort(-scores, kind="stable")[:limit]
    return [
        Hit(
            record_id=rows[i][0],
            text=rows[i][2],
            score=float(scores[i]),
            lane="dense",
            conversation_id=rows[i][3],
            source_sha256=rows[i][4],
            authored_at=rows[i][5],
            provider=rows[i][6],
        )
        for i in order
    ]
