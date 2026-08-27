"""Persist embedding vectors for records."""

import sqlite3

import numpy as np

_GUARDED_INSERT = """
INSERT OR REPLACE INTO vectors (record_id, vector)
SELECT record_id, ? FROM records WHERE record_id = ? AND source_sha256 = ?
"""


def write_vectors(
    connection: sqlite3.Connection,
    rows: list[tuple[str, str]],
    matrix: np.ndarray,
) -> int:
    """Store one float32 vector per (record_id, source_sha256), skipping stale ones.

    The insert is guarded by the revision hash the text was read at: embedding
    takes seconds, and a reconciliation landing in between would otherwise leave
    a vector computed from superseded text attached to the new revision --
    indistinguishable from a healthy vector once stored. A skipped row simply
    stays unembedded and the next embed run picks up its current revision.

    The caller owns the transaction, exactly as with records.
    """
    if len(rows) != len(matrix):
        raise ValueError("rows and matrix must correspond one to one")
    written = 0
    for (record_id, source_sha256), vector in zip(rows, matrix, strict=True):
        cursor = connection.execute(
            _GUARDED_INSERT,
            (np.asarray(vector, dtype=np.float32).tobytes(), record_id, source_sha256),
        )
        written += cursor.rowcount
    return written
