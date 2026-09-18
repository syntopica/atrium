"""Shortlist the curated pages a claim could belong to, by page rather than chunk."""

from atrium.curate.dense_page_hits import dense_page_hits
from atrium.curate.lexical_page_hits import lexical_page_hits
from atrium.curate.page_candidate import PageCandidate
from atrium.curate.page_library import PageLibrary

# The five curated folders. `brain/inbox/` and the repository's own documents
# are indexed under the same provider and are not destinations: the inbox is
# unreviewed material waiting to be folded, not a page a claim can join.
_FOLDERS = (
    "brain/projects/",
    "brain/topics/",
    "brain/business/",
    "brain/personal/",
    "brain/people/",
)
# Each lane contributes this many chunks; several chunks of one page collapse
# to that page's best chunk, so the chunk depth has to exceed the page depth by
# a wide margin or one long page crowds the shortlist out.
_DEPTH = 40
# Reciprocal rank fusion, the constant the retrieval package already uses.
_K = 60


def page_shortlist(library: PageLibrary, claim: str, limit: int = 5) -> list[PageCandidate]:
    """Return the pages both lanes agree are plausible destinations for ``claim``."""
    lanes = (
        lexical_page_hits(library, claim, _DEPTH),
        dense_page_hits(library, library.embedder.embed([claim])[0], _DEPTH),
    )
    fused: dict[str, float] = {}
    best: dict[str, PageCandidate] = {}
    for hits in lanes:
        seen: set[str] = set()
        for rank, hit in enumerate(hits):
            if not hit.path.startswith(_FOLDERS) or hit.path in seen:
                continue
            seen.add(hit.path)
            fused[hit.path] = fused.get(hit.path, 0.0) + 1.0 / (_K + rank + 1)
            if hit.path not in best or hit.lane == "dense":
                best[hit.path] = hit
    ranked = sorted(fused, key=lambda path: (-fused[path], path))[:limit]
    return [
        PageCandidate(
            path=path,
            title=best[path].title,
            score=round(fused[path], 6),
            lane="fused",
            excerpt=best[path].excerpt,
        )
        for path in ranked
    ]
