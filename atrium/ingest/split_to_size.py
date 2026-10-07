"""Pack a section's paragraphs into bounded chunks."""

from atrium.ingest.hard_split import hard_split
from atrium.ingest.max_chunk_chars import MAX_CHUNK_CHARS


def split_to_size(section: str) -> list[str]:
    """Return ``section`` as chunks of whole paragraphs, each within the size bound."""
    if len(section) <= MAX_CHUNK_CHARS:
        return [section]
    pieces: list[str] = []
    current = ""
    for paragraph in section.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph.strip()
        if len(candidate) > MAX_CHUNK_CHARS and current:
            pieces.append(current)
            current = paragraph.strip()
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [slice_ for piece in pieces for slice_ in hard_split(piece)]
