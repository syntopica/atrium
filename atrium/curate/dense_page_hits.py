"""The paraphrase lane over curated pages: a Spanish claim, an English page."""

import numpy as np

from atrium.curate.page_candidate import PageCandidate
from atrium.curate.page_library import PageLibrary


def dense_page_hits(
    library: PageLibrary, claim_vector: np.ndarray, limit: int = 20
) -> list[PageCandidate]:
    """Return curated chunks whose vectors are nearest to the claim's.

    Full scan on purpose: the curated layer is 4,889 chunks against the index's
    1.4 million records, so the matrix is a few megabytes and an approximate
    structure would buy nothing.
    """
    if not library.embedded:
        return []
    scores = library.matrix @ np.asarray(claim_vector, dtype=np.float32)
    order = np.argsort(-scores, kind="stable")[:limit]
    return [
        PageCandidate(
            path=library.paths[library.embedded[i]],
            title=library.titles[library.embedded[i]],
            score=float(scores[i]),
            lane="dense",
            excerpt=library.texts[library.embedded[i]],
        )
        for i in order
    ]
