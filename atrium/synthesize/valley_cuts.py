"""Episode cuts at TextTiling similarity valleys."""

from typing import Any

from atrium.synthesize.idf_cosine import idf_cosine
from atrium.synthesize.idf_weights import idf_weights
from atrium.synthesize.merge_vectors import merge_vectors
from atrium.synthesize.tf_vector import tf_vector

_WINDOW = 3  # turn blocks on each side of a candidate boundary
_MIN_BLOCKS_BETWEEN_CUTS = 2


def valley_cuts(blocks: list[dict[str, Any]]) -> set[int]:
    """Return boundaries deeper than the median depth plus one MAD, spaced apart."""
    vectors = [tf_vector(block["human_text"]) for block in blocks]
    idf = idf_weights(vectors)
    depths: dict[int, float] = {}
    for boundary in range(1, len(blocks)):
        left = merge_vectors(vectors[max(0, boundary - _WINDOW) : boundary])
        right = merge_vectors(vectors[boundary : boundary + _WINDOW])
        depths[boundary] = 1.0 - idf_cosine(left, right, idf)
    if not depths:
        return set()
    values = sorted(depths.values())
    median = values[len(values) // 2]
    mad = sorted(abs(value - median) for value in values)[len(values) // 2]
    threshold = median + mad
    cuts: set[int] = set()
    last_cut = 0
    for boundary in sorted(depths):
        if depths[boundary] > threshold and boundary - last_cut >= _MIN_BLOCKS_BETWEEN_CUTS:
            cuts.add(boundary)
            last_cut = boundary
    return cuts
