"""Measure the key characters that open a text."""

import re

_LEADING = re.compile(r"(?:\\+[rn]|[A-Za-z0-9+/=])*")


def leading_key_material_length(text: str) -> int:
    r"""How many base64 characters and ``\n`` escapes open ``text``."""
    match = _LEADING.match(text)
    return 0 if match is None else match.end()
