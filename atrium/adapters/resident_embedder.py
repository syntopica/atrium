"""The embedder the long-lived MCP process builds once and reuses."""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atrium.embed.embedder import Embedder

# Constructing the embedder costs seconds, which is most of what a one-shot
# `atrium search` spends. This process outlives a request, so it is built once
# on the first query that needs it and reused for the life of the server. Tools
# run in worker threads, so the build is serialized under a lock -- the first
# two concurrent searches would otherwise each build one and one would be
# thrown away after paying for it. (Not lru_cache: it does not lock the miss
# path, so both threads would still construct.)
_embedder = None
_embedder_lock = threading.Lock()


def resident_embedder() -> "Embedder":
    """Return the process-wide embedder, building it on first use."""
    global _embedder  # noqa: PLW0603 -- module singleton; the lock is the point
    with _embedder_lock:
        if _embedder is None:
            from atrium.embed.embedder import Embedder

            _embedder = Embedder()
        return _embedder
