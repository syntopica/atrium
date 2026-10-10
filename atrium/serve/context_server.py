"""The Unix-socket server that keeps the embedder and the matrix resident."""

import socketserver
from pathlib import Path
from typing import TYPE_CHECKING

from atrium.serve.context_request_handler import ContextRequestHandler

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder
    from atrium.serve.dense_matrix_holder import DenseMatrixHolder


class ContextServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """Serve each request in its own thread.

    A request abandoned by a client that timed out must not hold up the next
    prompt's request behind it.
    """

    daemon_threads = True

    def __init__(
        self,
        socket_path: Path,
        index: Path,
        holder: "DenseMatrixHolder",
        embedder: "ContextEmbedder",
    ) -> None:
        """Bind the socket; the caller owns its lifetime and permissions."""
        self.index = index
        self.holder = holder
        self.embedder = embedder
        super().__init__(str(socket_path), ContextRequestHandler)
