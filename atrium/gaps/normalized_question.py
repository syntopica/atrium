"""One spelling per question, so repeats of it count together."""

import unicodedata


def normalized_question(text: str) -> str:
    """Casefold, NFKC, and collapse whitespace."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
