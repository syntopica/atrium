"""Tell a character of the base64 alphabet."""

import re


def is_base64_character(character: str) -> bool:
    """Whether one character belongs to the base64 alphabet."""
    return re.fullmatch(r"[A-Za-z0-9+/=]", character) is not None
