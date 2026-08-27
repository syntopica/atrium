"""Persist embedding vectors for records."""

import sqlite3

import numpy as np


def write_vectors(connection: sqlite3.Connection, record_ids: list[str], matrix: np.ndarray) -> int:
    """Store one float32 vector per record id, replacing any previous vector.

    The caller owns the transaction, exactly as with records: a vector must
    never commit without the record revision it was computed from.
    """
    if len(record_ids) != len(matrix):
        raise ValueError("record_ids and matrix rows must correspond one to one")
    rows = [
        (record_id, np.asarray(vector, dtype=np.float32).tobytes())
        for record_id, vector in zip(record_ids, matrix, strict=True)
    ]
    connection.executemany("INSERT OR REPLACE INTO vectors (record_id, vector) VALUES (?, ?)", rows)
    return len(rows)
