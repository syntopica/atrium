"""Rank in memory, then read only the winning records from the index."""

import sqlite3

import numpy as np

from atrium.context.dense_matrix import DenseMatrix
from atrium.context.dense_matrix_scope import dense_matrix_scope
from atrium.retrieve.hit import Hit
from atrium.sql.load_sql import load_sql


def dense_matrix_hits(  # noqa: PLR0913 -- same contract as dense_hits plus the matrix
    connection: sqlite3.Connection,
    matrix: DenseMatrix,
    vector: np.ndarray,
    limit: int,
    *,
    curated: bool,
    workspace: str | None = None,
) -> list[Hit]:
    """Return what dense_hits returns, touching the index for ``limit`` rows only.

    A matrix older than the index can name records that have since gone; those
    are skipped and the next candidates read instead, so a stale copy loses
    recall for what changed but never returns a deleted record.
    """
    rows = np.flatnonzero(dense_matrix_scope(matrix, curated=curated, workspace=workspace))
    if not len(rows):
        return []
    scores = matrix.vectors[rows] @ np.asarray(vector, dtype=np.float32)
    if not np.isfinite(scores).all():
        raise ValueError("invalid context vector scores")
    order = rows[np.argsort(-scores, kind="stable")]
    by_row = dict(zip(rows.tolist(), scores.tolist(), strict=True))
    hits: list[Hit] = []
    for start in range(0, len(order), max(limit * 2, 16)):
        batch = order[start : start + max(limit * 2, 16)]
        ids = [str(matrix.ids[i]) for i in batch]
        found = {
            row[0]: row
            for row in connection.execute(
                load_sql("context/records_by_ids").format(placeholders=",".join("?" * len(ids))),
                ids,
            )
        }
        for position, record_id in zip(batch.tolist(), ids, strict=True):
            row = found.get(record_id)
            if row is None:
                continue
            hits.append(
                Hit(
                    row[0],
                    row[1],
                    by_row[position],
                    "dense",
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                )
            )
            if len(hits) == limit:
                return hits
    return hits
