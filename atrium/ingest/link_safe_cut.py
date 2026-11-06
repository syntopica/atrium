"""Move a positional cut back to the start of a link it would split."""

from atrium.ingest.link_span import LINK_SPAN


def link_safe_cut(text: str, start: int, end: int) -> int:
    """Return the cut for ``text[start:end]``: ``end``, or earlier if a link straddles it.

    A link that begins at or before ``start`` is longer than a chunk and is cut
    where it falls, so the bound and the forward progress both hold.
    """
    if end >= len(text):
        return len(text)
    for match in LINK_SPAN.finditer(text, max(start, end - 512), min(len(text), end + 512)):
        if match.start() < end < match.end():
            return match.start() if match.start() > start else end
    return end
