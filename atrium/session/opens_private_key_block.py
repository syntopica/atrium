"""Tell the opening line of a PEM private key block."""

import re

from atrium.session.is_private_key_marker_line import is_private_key_marker_line


def opens_private_key_block(line: str) -> bool:
    """Whether the line is a bare ``-----BEGIN ... PRIVATE KEY-----`` marker.

    A BEGIN marker followed by other text is prose about a key, and opening a
    block on it took the 141 lines after it (2026-11-06). The decision is made on
    this line alone: an open block runs to its END line whatever its body lines
    look like, so a key printed with line numbers still goes whole.
    """
    return (
        is_private_key_marker_line(line, "BEGIN")
        and re.search(r"PRIVATE KEY-----\s*$", line) is not None
    )
