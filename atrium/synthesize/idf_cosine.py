"""IDF-weighted cosine similarity of two term-frequency vectors."""

import math
from collections import Counter


def idf_cosine(left: Counter[str], right: Counter[str], idf: dict[str, float]) -> float:
    """Return the IDF-weighted cosine of ``left`` and ``right``; 0.0 when either is empty."""
    if not left or not right:
        return 0.0
    dot = sum(count * right[word] * idf.get(word, 1.0) ** 2 for word, count in left.items())
    norm_left = math.sqrt(sum((count * idf.get(word, 1.0)) ** 2 for word, count in left.items()))
    norm_right = math.sqrt(sum((count * idf.get(word, 1.0)) ** 2 for word, count in right.items()))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)
