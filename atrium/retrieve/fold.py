"""Strip diacritics the way the index tokenizer does (remove_diacritics 2)."""

import unicodedata


def fold(text: str) -> str:
    """Return ``text`` without combining marks, for comparison against the index.

    The tokenizer removes diacritics, so a verifier built over raw text throws
    away a legitimate hit: `café-au-lait` must find a stored `cafe-au-lait`
    (reproduced by review).
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
