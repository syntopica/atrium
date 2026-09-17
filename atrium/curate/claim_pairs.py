"""Which claims are close enough to be worth adjudicating as a pair."""

import numpy as np

from atrium.context.context_embedder import ContextEmbedder


def claim_pairs(
    texts: list[str], embedder: ContextEmbedder, threshold: float, neighbours: int
) -> list[tuple[int, int, float]]:
    """Return (left, right, similarity) for the near neighbours of each claim.

    Exact cosine over an in-memory matrix, not an approximate index: 497 claims
    are 123,753 pairs and 765 KB of vectors, so the whole similarity matrix
    fits and an ANN index would add a dependency, a build step and a recall
    question for nothing. The full ledger is where ANN starts to matter --
    288,844 claims are 41.7 billion pairs and 444 MB of vectors.

    Each claim keeps its strongest ``neighbours`` above ``threshold``, and a
    pair is emitted once, ordered, so the adjudication cost is bounded by
    ``len(texts) * neighbours`` rather than by the square.
    """
    if not texts:
        return []
    matrix = embedder.embed(texts)
    similarity = matrix @ matrix.T
    np.fill_diagonal(similarity, -1.0)
    found: dict[tuple[int, int], float] = {}
    for left in range(len(texts)):
        row = similarity[left]
        top = np.argsort(row)[::-1][:neighbours]
        for right in top:
            score = float(row[right])
            if score < threshold:
                break
            key = (min(left, int(right)), max(left, int(right)))
            found[key] = max(found.get(key, score), score)
    return sorted(
        ((left, right, score) for (left, right), score in found.items()), key=lambda p: -p[2]
    )
