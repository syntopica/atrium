"""Tell one of the two RFC 1421 headers an encrypted PEM key carries."""

import re


def is_pem_header_line(line: str) -> bool:
    """Whether the line is ``Proc-Type: ...`` or ``DEK-Info: ...``.

    Any ``word: value`` line read as a header on 2026-11-06: a config listing
    after a double-escaped key opened a block and lost its hosts and key paths.
    Same rule as scribe's `isPemHeaderLine`.
    """
    return re.match(r"(?:Proc-Type|DEK-Info): \S", line.strip()) is not None
