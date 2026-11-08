"""Supply exactly the frozen document and query vectors to every system."""

import numpy as np


class CachedEmbedder:
    """Fail closed when a backend requests text outside the frozen experiment."""

    def __init__(self, documents: dict[str, np.ndarray], queries: dict[str, np.ndarray]):
        self.documents = documents
        self.queries = queries

    def embed(self, text, memory_action=None):
        """Implement both Mem0's scalar and Atrium's batch embedding contracts."""
        if isinstance(text, list):
            return np.asarray([self.queries[value] for value in text], dtype=np.float32)
        values = self.documents if memory_action == "add" else self.queries
        return values[text].tolist()
