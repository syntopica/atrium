"""Rebuild the matrix after a refresh, before any prompt has to notice."""

import sqlite3
import time
from typing import TYPE_CHECKING

from atrium.context.read_dense_generation import read_dense_generation
from atrium.store.open_store import open_store

if TYPE_CHECKING:
    from pathlib import Path

    from atrium.serve.dense_matrix_holder import DenseMatrixHolder


def watch_dense_generation(index: "Path", holder: "DenseMatrixHolder", interval: float) -> None:
    """Poll the counter forever; meant for a daemon thread."""
    while True:
        time.sleep(interval)
        try:
            connection = open_store(index, read_only=True)
            try:
                live = read_dense_generation(connection)
            finally:
                connection.close()
        except (OSError, sqlite3.Error, RuntimeError):
            continue
        holder.refresh(live)
