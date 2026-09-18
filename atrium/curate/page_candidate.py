"""One curated page proposed as the destination for a claim."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageCandidate:
    """A page path with the passage that made it a candidate."""

    path: str
    title: str
    score: float
    lane: str
    excerpt: str
