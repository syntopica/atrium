"""The sum of several term-frequency vectors."""

from collections import Counter


def merge_vectors(vectors: list[Counter[str]]) -> Counter[str]:
    """Return the word counts of ``vectors`` added together."""
    merged: Counter[str] = Counter()
    for vector in vectors:
        merged.update(vector)
    return merged
