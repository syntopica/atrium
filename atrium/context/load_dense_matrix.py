"""Read a saved dense matrix, refusing anything malformed."""

from pathlib import Path

import numpy as np

from atrium.context.dense_matrix import DenseMatrix


def load_dense_matrix(path: Path) -> DenseMatrix | None:
    """Return the saved matrix, or None when it is missing or unreadable.

    ``allow_pickle`` stays off: the file holds plain arrays only, and a pickled
    object in a derived cache would be code run on load.
    """
    try:
        with np.load(path, allow_pickle=False) as saved:
            generation = int(saved["generation"])
            matrix = DenseMatrix(
                None if generation < 0 else generation,
                saved["ids"],
                saved["roles"],
                saved["workspaces"],
                saved["vectors"].astype(np.float32, copy=False),
            )
    except (OSError, ValueError, KeyError):
        return None
    rows = len(matrix.ids)
    if not (len(matrix.roles) == len(matrix.workspaces) == len(matrix.vectors) == rows):
        return None
    if not np.isfinite(matrix.vectors).all():
        return None
    return matrix
