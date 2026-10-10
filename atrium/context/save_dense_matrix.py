"""Write a dense matrix beside the index so a restart need not rebuild it."""

import os
from pathlib import Path

import numpy as np

from atrium.context.dense_matrix import DenseMatrix


def save_dense_matrix(matrix: DenseMatrix, path: Path) -> None:
    """Publish atomically: readers see the old file or the complete new one.

    The file is derived and per machine, like the index it copies: never sync
    it, rebuild it.
    """
    partial = path.with_name(path.name + ".partial")
    with partial.open("wb") as handle:
        np.savez(
            handle,
            generation=np.array(-1 if matrix.generation is None else matrix.generation),
            ids=matrix.ids,
            roles=matrix.roles,
            workspaces=matrix.workspaces,
            vectors=matrix.vectors,
        )
        handle.flush()
        os.fsync(handle.fileno())
    partial.replace(path)
