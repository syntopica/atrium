"""Inverse document frequency over a session's blocks."""

import math
from collections import Counter


def idf_weights(vectors: list[Counter[str]]) -> dict[str, float]:
    """Return the smoothed IDF weight of every word across ``vectors``."""
    documents = max(len(vectors), 1)
    frequency: Counter[str] = Counter()
    for vector in vectors:
        frequency.update(set(vector))
    return {word: math.log(documents / (1 + count)) + 1.0 for word, count in frequency.items()}
