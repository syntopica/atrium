"""Defer model loading until retrieval actually requires a vector."""

from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from atrium.embed.embedder import Embedder


class LazyEmbedder:
    """Share one model per request, or use a resident adapter's factory."""

    def __init__(self, factory: "Callable[[], Embedder] | None" = None) -> None:
        self.factory = factory
        self.instance: Embedder | None = None

    def embed(self, texts: list[str]) -> np.ndarray:
        """Load the configured model only when a dense lane asks for it."""
        if self.instance is None:
            if self.factory is not None:
                self.instance = self.factory()
            else:
                from atrium.embed.embedder import Embedder

                self.instance = Embedder()
        return self.instance.embed(texts)
