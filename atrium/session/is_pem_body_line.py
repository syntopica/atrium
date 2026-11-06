"""Tell a line that can sit inside a PEM block."""

import re


def is_pem_body_line(line: str) -> bool:
    """Whether the line is base64, an RFC 1421 header such as ``Proc-Type: 4,ENCRYPTED``, or blank.

    A block that meets any other line was a BEGIN marker quoted in prose, not a
    key, and ends there: one took the 141 lines after it on 2026-11-06.
    """
    trimmed = line.strip()
    return (
        not trimmed
        or re.fullmatch(r"[A-Za-z0-9+/=]+", trimmed) is not None
        or re.match(r"[A-Za-z-]+: \S", trimmed) is not None
    )
