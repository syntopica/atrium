"""The reranker the long-lived MCP process builds once and reuses."""

import threading

from atrium.rerank.cross_encoder import CrossEncoder

# Construction is cheap and loading is lazy and locked inside the encoder, so
# one shared instance is all this needs; the lock only keeps two first calls
# from building two.
_reranker: CrossEncoder | None = None
_reranker_lock = threading.Lock()


def resident_reranker() -> CrossEncoder:
    """Return the process-wide reranker, building it on first use."""
    global _reranker  # noqa: PLW0603 -- module singleton; the lock is the point
    with _reranker_lock:
        if _reranker is None:
            _reranker = CrossEncoder()
        return _reranker
