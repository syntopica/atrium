"""Tell a line inside an open PEM block that is part of the key."""

import re

from atrium.session.is_base64_character import is_base64_character
from atrium.session.pem_body_prefix_max_length import PEM_BODY_PREFIX_MAX_LENGTH


def is_pem_body_line(line: str) -> bool:
    r"""Whether the line is blank, an RFC 1421 header, or base64 behind a short prefix.

    The prefix has at most `PEM_BODY_PREFIX_MAX_LENGTH` characters and no letters
    (``   12\t``, ``> ``, ``│ ``), as printouts number or quote a key. Any other
    line ends the block and stays: running a block to its END line took a whole
    database listing after a truncated key on 2026-11-06. Same rule as scribe's
    `isPemBodyLine`.
    """
    trimmed = line.rstrip()
    if trimmed.strip() == "":
        return True
    if re.match(r"[A-Za-z-]+: \S", trimmed.lstrip()):
        return True
    start = len(trimmed)
    while start > 0 and is_base64_character(trimmed[start - 1]):
        start -= 1
    prefix = trimmed[:start]
    return (
        len(trimmed) - start >= 4  # noqa: PLR2004 -- one base64 quantum
        and len(prefix) <= PEM_BODY_PREFIX_MAX_LENGTH
        and re.search(r"[A-Za-z]", prefix) is None
    )
