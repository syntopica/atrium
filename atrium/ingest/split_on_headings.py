"""Split a note into its heading-delimited sections."""

import re
from itertools import pairwise

_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)


def split_on_headings(text: str) -> list[str]:
    """Return the non-empty sections of ``text``, each starting at a heading."""
    starts = [match.start() for match in _HEADING.finditer(text)]
    if not starts:
        return [text.strip()] if text.strip() else []
    bounds = ([0] if starts[0] != 0 else []) + starts + [len(text)]
    sections = [text[a:b].strip() for a, b in pairwise(bounds)]
    return [section for section in sections if section]
