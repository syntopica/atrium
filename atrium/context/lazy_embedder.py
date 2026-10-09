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
        # One entry, not a cache: a context request embeds its query once for
        # the curated pass and again for the history pass, and the second
        # forward pass cost ~0.14 s of a ~2.5 s request (measured 2026-10-09).
        # Keeping only the last call bounds memory when the instance is resident.
        self.last: tuple[tuple[str, ...], np.ndarray] | None = None

    def embed(self, texts: list[str]) -> np.ndarray:
        """Load the configured model only when a dense lane asks for it."""
        if self.instance is None:
            if self.factory is not None:
                self.instance = self.factory()
            else:
                from atrium.embed.embedder import Embedder

                self.instance = Embedder()
        key = tuple(texts)
        if self.last is not None and self.last[0] == key:
            return self.last[1]
        vectors = self.instance.embed(texts)
        self.last = (key, vectors)
        return vectors
