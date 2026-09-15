"""The minimal embedding capability required by context retrieval."""

from typing import Protocol

import numpy as np


class ContextEmbedder(Protocol):
    """Accept both the existing model and a resident lazy adapter."""

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return one vector for each supplied text."""
        ...
