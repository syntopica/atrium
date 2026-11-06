"""Tell a line carrying an escaped private key."""

import re


def holds_escaped_private_key(line: str) -> bool:
    r"""Whether a ``PRIVATE KEY-----`` marker is followed by a literal ``\n`` escape.

    One backslash, or more when the JSON was escaped again.

    JSON and tool output print a key on one line; such a line is not the opening
    line of a block, whether or not truncation kept its END marker.
    """
    return re.search(r"PRIVATE KEY-----\\+[rn]", line) is not None
