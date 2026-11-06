"""Tell a line that reads as part of a PEM body."""

import re


def looks_like_pem_body_line(line: str | None) -> bool:
    """Whether the line ends in 40 base64 characters, or is an RFC 1421 header.

    The base64 run may follow any prefix a printout put before it; a header looks
    like ``Proc-Type: 4,ENCRYPTED``.
    """
    if line is None:
        return False
    return (
        re.search(r"[A-Za-z0-9+/=]{40}$", line.rstrip()) is not None
        or re.match(r"[A-Za-z-]+: \S", line.lstrip()) is not None
    )
