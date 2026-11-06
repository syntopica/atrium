"""Tell a one-line escaped private key from the opening line of a block."""

import re


def closes_private_key_on_same_line(line: str) -> bool:
    r"""Whether a ``-----BEGIN ... PRIVATE KEY-----`` line also holds its END marker.

    A JSON-escaped key sits on one line with ``\n`` escapes. Read as the opening
    line of a block it never meets an END line, and the rest of the text went
    with it (141 lines of one session, 2026-11-06). Such a line is left to the
    vendor pattern, which removes the key and keeps the rest of the line.
    """
    return re.search(r"-----END [A-Z0-9 ]*PRIVATE KEY-----", line) is not None
