"""Where the resident service keeps its copy of the index's vectors."""

from pathlib import Path


def dense_matrix_file(state: Path) -> Path:
    """Place the derived matrix beside the index it was copied from."""
    return state / "dense-matrix.npz"
