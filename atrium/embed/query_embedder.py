"""Build the embedder every retrieval query goes through."""

from atrium.embed.embedder import Embedder
from atrium.embed.query_prefix import QUERY_PREFIX


def query_embedder() -> Embedder:
    """Return an embedder for queries; stored vectors use ``Embedder()``'s default."""
    return Embedder(QUERY_PREFIX)
