"""Tell a line that reads as part of a PEM body."""

import re

from atrium.session.is_pem_header_line import is_pem_header_line


def looks_like_pem_body_line(line: str | None) -> bool:
    """Whether the line ends in 40 base64 characters, or is an RFC 1421 header.

    The base64 run may follow any prefix a printout put before it; a header is
    ``Proc-Type`` or ``DEK-Info``.
    """
    if line is None:
        return False
    return re.search(r"[A-Za-z0-9+/=]{40}$", line.rstrip()) is not None or is_pem_header_line(line)
