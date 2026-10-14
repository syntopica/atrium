"""The minimal reranking capability context retrieval accepts."""

from typing import Protocol


class ContextReranker(Protocol):
    """Score how well each text answers one query, higher is better."""

    def score(self, query: str, texts: list[str], deadline: float) -> list[float]:
        """Return one score per text, or raise ``TimeoutError`` past ``deadline``.

        ``deadline`` is a ``time.monotonic()`` value.
        """
        ...
