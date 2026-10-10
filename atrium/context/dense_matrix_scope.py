"""Select the matrix rows one context pass may rank, mirroring context_scope."""

import numpy as np

from atrium.context.dense_matrix import DenseMatrix


def dense_matrix_scope(matrix: DenseMatrix, *, curated: bool, workspace: str | None) -> np.ndarray:
    """Return a boolean mask with the same role and workspace rules as the SQL path.

    Curated notes ignore the workspace; history excludes notes and third-party
    sources and, when scoped, keeps the workspace itself and everything under it.
    """
    if curated:
        notes: np.ndarray = matrix.roles == "note"
        return notes
    history: np.ndarray = (matrix.roles != "source") & (matrix.roles != "note")
    if workspace is None:
        return history
    prefix = workspace.rstrip("/") + "/"
    inside: np.ndarray = (matrix.workspaces == workspace) | np.char.startswith(
        matrix.workspaces, prefix
    )
    scoped: np.ndarray = history & inside
    return scoped
