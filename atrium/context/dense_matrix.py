"""Every embedded vector of an index, held outside it for fast ranking."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DenseMatrix:
    """Row i of ``vectors`` belongs to ``ids[i]``, ``roles[i]`` and ``workspaces[i]``.

    ``generation`` is the index's vector-change counter when the rows were read,
    or None for an index that predates the counter; a reader compares it with
    the live counter to know whether this copy is current.
    """

    generation: int | None
    ids: np.ndarray
    roles: np.ndarray
    workspaces: np.ndarray
    vectors: np.ndarray
