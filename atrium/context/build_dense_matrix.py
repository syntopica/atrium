"""Copy every embedded vector out of the index in one consistent snapshot."""

import sqlite3

import numpy as np

from atrium.context.dense_matrix import DenseMatrix
from atrium.context.read_dense_generation import read_dense_generation
from atrium.embed.semantic_roles import SEMANTIC_ROLES
from atrium.sql.load_sql import load_sql


def build_dense_matrix(connection: sqlite3.Connection) -> DenseMatrix:
    """Read the counter and the rows inside one read transaction.

    Under WAL a read transaction sees one snapshot, so the generation stamped on
    the matrix is exactly the one its rows came from, even while a refresh
    writes. Text is never copied: ranking needs ids and vectors, and the few
    winners are fetched from the index afterwards.
    """
    placeholders = ",".join("?" * len(SEMANTIC_ROLES))
    connection.execute(load_sql("context/begin_read"))
    try:
        generation = read_dense_generation(connection)
        rows = connection.execute(
            load_sql("context/dense_matrix_rows").format(placeholders=placeholders),
            SEMANTIC_ROLES,
        ).fetchall()
    finally:
        connection.execute(load_sql("context/end_read"))
    vectors = (
        np.frombuffer(b"".join(row[3] for row in rows), dtype=np.float32).reshape(len(rows), -1)
        if rows
        else np.zeros((0, 0), dtype=np.float32)
    )
    if not np.isfinite(vectors).all():
        raise ValueError("the index holds a non-finite vector")
    return DenseMatrix(
        generation,
        np.array([row[0] for row in rows], dtype=str),
        np.array([row[1] for row in rows], dtype=str),
        np.array([row[2] or "" for row in rows], dtype=str),
        vectors,
    )
