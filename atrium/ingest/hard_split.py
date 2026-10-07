"""Positional cutting of an oversized chunk."""

from atrium.ingest.max_chunk_chars import MAX_CHUNK_CHARS


def hard_split(piece: str) -> list[str]:
    """Bound even a single unbroken paragraph.

    Paragraph packing alone let a 17,999-character table through (reproduced by
    review), and past the embedder's 2,048-token truncation the tail of such a
    chunk contributes nothing to its vector -- two long texts differing only in
    their tails embedded byte-identically. The cut is positional, so it stays
    deterministic across machines.
    """
    if len(piece) <= MAX_CHUNK_CHARS:
        return [piece]
    return [
        piece[start : start + MAX_CHUNK_CHARS] for start in range(0, len(piece), MAX_CHUNK_CHARS)
    ]
