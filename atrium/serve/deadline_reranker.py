"""A reranker that never works past the moment its client stops waiting."""

from typing import TYPE_CHECKING

from atrium.context.finish_margin_s import FINISH_MARGIN_S

if TYPE_CHECKING:
    from atrium.context.context_reranker import ContextReranker


class DeadlineReranker:
    """Cut every rerank deadline to the client's, less the time the reply needs.

    The owner's rerank budget still applies; this only ends it earlier when
    the client would give up first. Scoring past that point burns CPU for an
    answer nobody reads, and under load it turned every prompt into a
    ``service_timeout`` (28 of 29 calls, 2026-10-18).
    """

    def __init__(self, reranker: "ContextReranker", client_deadline: float) -> None:
        """Wrap ``reranker``; ``client_deadline`` is a ``time.monotonic()`` value."""
        self._reranker = reranker
        self._deadline = client_deadline - FINISH_MARGIN_S

    def score(self, query: str, texts: list[str], deadline: float) -> list[float]:
        """Score with the earlier of the two deadlines."""
        return self._reranker.score(query, texts, min(deadline, self._deadline))
