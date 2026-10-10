"""Keep one current dense matrix in memory and rebuild it off the request path."""

import sys
import threading
from pathlib import Path

from atrium.context.build_dense_matrix import build_dense_matrix
from atrium.context.dense_matrix import DenseMatrix
from atrium.context.load_dense_matrix import load_dense_matrix
from atrium.context.read_dense_generation import read_dense_generation
from atrium.context.save_dense_matrix import save_dense_matrix
from atrium.store.open_store import open_store


class DenseMatrixHolder:
    """The served matrix, its file, and at most one rebuild at a time.

    Copying the vectors out of a cold 22 GB index takes a minute or more on a
    loaded machine, which is exactly what a prompt cannot wait for. So a request
    always ranks the matrix already in memory; when the index has moved past it,
    the request says so in a warning and a background thread builds the next
    one, swapped in only once complete.
    """

    def __init__(self, index: Path, cache: Path) -> None:
        """Hold nothing yet; ``prepare`` loads or builds the first matrix."""
        self.index = index
        self.cache = cache
        self.matrix: DenseMatrix | None = None
        self._lock = threading.Lock()
        self._rebuild: threading.Thread | None = None

    def prepare(self) -> None:
        """Load the saved matrix when it is current, else build one before serving."""
        saved = load_dense_matrix(self.cache)
        connection = open_store(self.index, read_only=True)
        try:
            live = read_dense_generation(connection)
            if saved is not None and live is not None and saved.generation == live:
                self.matrix = saved
                return
            self.matrix = build_dense_matrix(connection)
        finally:
            connection.close()
        save_dense_matrix(self.matrix, self.cache)

    def current(self, live: int | None) -> tuple[DenseMatrix | None, list[str]]:
        """Return the matrix to rank and the warnings a reader must see with it."""
        with self._lock:
            matrix = self.matrix
        if matrix is None:
            return None, ["dense_matrix_unavailable"]
        if live is None:
            return matrix, ["dense_generation_missing"]
        if matrix.generation != live:
            self.refresh(live)
            return matrix, ["dense_matrix_stale_rebuilding"]
        return matrix, []

    def refresh(self, live: int | None) -> None:
        """Start one background rebuild unless the matrix is current or one runs."""
        with self._lock:
            matrix = self.matrix
            if matrix is not None and live is not None and matrix.generation == live:
                return
            if self._rebuild is not None and self._rebuild.is_alive():
                return
            self._rebuild = threading.Thread(target=self._build, daemon=True)
            self._rebuild.start()

    def _build(self) -> None:
        try:
            connection = open_store(self.index, read_only=True)
            try:
                matrix = build_dense_matrix(connection)
            finally:
                connection.close()
            save_dense_matrix(matrix, self.cache)
        except Exception as error:
            print(f"atrium serve-context: rebuild failed: {error}", file=sys.stderr, flush=True)
            return
        with self._lock:
            self.matrix = matrix
