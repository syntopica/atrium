"""Run the resident context service until the process is stopped."""

import os
import socket
import sys
import threading
import time
from pathlib import Path

from atrium.context.lazy_embedder import LazyEmbedder
from atrium.embed.query_embedder import query_embedder
from atrium.rerank.cross_encoder import CrossEncoder
from atrium.serve.context_server import ContextServer
from atrium.serve.context_socket_path import context_socket_path
from atrium.serve.dense_matrix_file import dense_matrix_file
from atrium.serve.dense_matrix_holder import DenseMatrixHolder
from atrium.serve.watch_dense_generation import watch_dense_generation


def serve_context(index: Path, state: Path, interval: float = 60.0) -> int:
    """Warm everything a prompt needs, then answer on the state's socket.

    The per-prompt CLI spent its budget starting Python, loading the model and
    scanning the index; this process pays those once. It refuses to start when
    another live service already owns the socket, and replaces a dead one's.
    """
    path = context_socket_path(state)
    if path.exists():
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(path))
        except OSError:
            path.unlink()
        else:
            # Exit 0: a supervisor that restarts on failure must not respawn a
            # second copy forever against the one already serving.
            print(f"atrium serve-context: {path} is already served", file=sys.stderr)
            return 0
        finally:
            probe.close()
    holder = DenseMatrixHolder(index, dense_matrix_file(state))
    holder.prepare()
    embedder = LazyEmbedder(query_embedder)
    embedder.embed(["warm-up"])
    # A reranker that cannot load (no network for the first download) costs
    # quality, not service: answers keep the fused order.
    reranker: CrossEncoder | None = None
    try:
        loaded = CrossEncoder()
        loaded.score("warm-up", ["warm-up"], time.monotonic() + 60)
        reranker = loaded
    except (OSError, RuntimeError, ValueError) as error:
        print(f"atrium serve-context: reranker unavailable: {error!r}", file=sys.stderr)
    old_mask = os.umask(0o077)
    try:
        server = ContextServer(path, index, holder, embedder, reranker)
    finally:
        os.umask(old_mask)
    threading.Thread(
        target=watch_dense_generation, args=(index, holder, interval), daemon=True
    ).start()
    rows = 0 if holder.matrix is None else len(holder.matrix.ids)
    print(f"atrium serve-context: serving {index} on {path} ({rows} vectors)", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        path.unlink(missing_ok=True)
    return 0
