"""Scan an embedded ledger for the pairs close enough to be one claim."""

import numpy as np

# One block of rows against the whole matrix. 500 rows by 288,844 columns of
# float32 is 578 MB of similarities, which is the largest intermediate worth
# holding; the whole matrix squared would be 334 TB.
_BLOCK = 500


def near_duplicate_pairs(
    matrix: np.ndarray, threshold: float, neighbours: int
) -> list[tuple[int, int, float]]:
    """Return (left, right, similarity) for every close pair, each pair once.

    Blocked matrix multiplication, not an approximate index: the exact scan of
    288,844 vectors is minutes of CPU and answers the question an ANN index
    would only approximate, which matters here because the number being
    measured is how much paraphrase the corpus actually holds.
    """
    total = matrix.shape[0]
    found: dict[tuple[int, int], float] = {}
    for start in range(0, total, _BLOCK):
        block = np.asarray(matrix[start : start + _BLOCK], dtype=np.float32)
        similarity = block @ np.asarray(matrix, dtype=np.float32).T
        for offset in range(block.shape[0]):
            row = similarity[offset]
            row[start + offset] = -1.0
            top = np.argpartition(row, -neighbours)[-neighbours:]
            for right in top:
                score = float(row[right])
                if score < threshold:
                    continue
                left = start + offset
                key = (min(left, int(right)), max(left, int(right)))
                found[key] = max(found.get(key, score), score)
    return sorted(
        ((left, right, score) for (left, right), score in found.items()), key=lambda pair: -pair[2]
    )
