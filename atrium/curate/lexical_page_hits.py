"""The exact-recall lane over curated pages: identifiers, paths, proper names."""

import math
import re

from atrium.curate.page_candidate import PageCandidate
from atrium.curate.page_library import PageLibrary
from atrium.retrieve.fold import fold

# A claim is a sentence, not a query: its common words match every page, so the
# score is inverse document frequency summed over the terms a chunk contains.
# The rare ones - `selectPendingDrafts`, `wrangler.jsonc` - carry the identity.
_MIN_LENGTH = 4
_WORD = re.compile(r"[a-z0-9_]+")


def lexical_page_hits(library: PageLibrary, claim: str, limit: int = 20) -> list[PageCandidate]:
    """Return curated chunks sharing rare words with ``claim``, best first."""
    terms = {term for term in _WORD.findall(fold(claim).lower()) if len(term) >= _MIN_LENGTH}
    weights = {}
    for term in terms:
        count = sum(1 for words in library.words if term in words)
        if count:
            weights[term] = math.log(len(library.words) / count)
    if not weights:
        return []
    scored = [
        (sum(weight for term, weight in weights.items() if term in words), index)
        for index, words in enumerate(library.words)
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [
        PageCandidate(
            path=library.paths[index],
            title=library.titles[index],
            score=score,
            lane="lexical",
            excerpt=library.texts[index],
        )
        for score, index in scored[:limit]
        if score > 0
    ]
