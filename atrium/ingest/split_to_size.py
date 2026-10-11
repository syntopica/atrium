"""Pack a section's paragraphs into bounded chunks."""

from atrium.ingest.hard_split import hard_split
from atrium.ingest.is_bare_heading import is_bare_heading
from atrium.ingest.max_chunk_chars import MAX_CHUNK_CHARS


def split_to_size(section: str) -> list[str]:
    """Return ``section`` as chunks of whole paragraphs, each within the size bound."""
    if len(section) <= MAX_CHUNK_CHARS:
        return [section]
    pieces: list[str] = []
    current = ""
    for paragraph in section.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph.strip()
        # A heading stays with the paragraph it introduces even when that
        # overflows: hard_split bounds the result, and a heading alone is a chunk
        # with a vector and no answer.
        if len(candidate) > MAX_CHUNK_CHARS and current and not is_bare_heading(current):
            pieces.append(current)
            current = paragraph.strip()
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [slice_ for piece in pieces for slice_ in hard_split(piece)]
