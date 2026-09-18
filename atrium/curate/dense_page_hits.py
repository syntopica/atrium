"""The paraphrase lane over curated pages: a Spanish claim, an English page."""

import sqlite3

import numpy as np

from atrium.curate.page_candidate import PageCandidate

_QUERY = """
SELECT r.conversation_id, r.title, v.vector, r.text
FROM vectors v
JOIN records r ON r.record_id = v.record_id
WHERE r.provider = 'brain'
ORDER BY v.record_id
"""


def dense_page_hits(
    connection: sqlite3.Connection, claim_vector: np.ndarray, limit: int = 20
) -> list[PageCandidate]:
    """Return curated pages whose chunks are nearest to the claim's vector.

    Full scan on purpose: the curated layer is 4,889 chunks against the index's
    1.4 million records, so the whole matrix is a few megabytes and an
    approximate structure would buy nothing.
    """
    rows = connection.execute(_QUERY).fetchall()
    if not rows:
        return []
    matrix = np.frombuffer(b"".join(row[2] for row in rows), dtype=np.float32).reshape(
        len(rows), -1
    )
    scores = matrix @ np.asarray(claim_vector, dtype=np.float32)
    order = np.argsort(-scores, kind="stable")[:limit]
    return [
        PageCandidate(
            path=rows[i][0],
            title=rows[i][1],
            score=float(scores[i]),
            lane="dense",
            excerpt=rows[i][3],
        )
        for i in order
    ]
