"""Map retrieval-normalized text back to the original character positions."""

from atrium.retrieve.fold import fold


def folded_text_offsets(text: str) -> tuple[str, list[int]]:
    """Preserve offsets when diacritics disappear or compatibility characters expand."""
    pieces = []
    offsets = []
    for position, character in enumerate(text):
        normalized = fold(character)
        pieces.append(normalized)
        offsets.extend([position] * len(normalized))
    return "".join(pieces), offsets
