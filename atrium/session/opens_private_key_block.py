"""Tell where a PEM private key block opens on a line."""

import re

from atrium.session.looks_like_pem_body_line import looks_like_pem_body_line

_BEGIN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")


def opens_private_key_block(line: str, following: str | None) -> int | None:
    """Return where a block opens on ``line``, or None when it opens none.

    Same rule as scribe's `opensPrivateKeyBlock`: a BEGIN marker anywhere in the
    line opens a block when nothing follows it, or when the next line reads as
    key body. A marker followed by text and then prose is prose about a key.
    """
    marker = _BEGIN.search(line)
    if marker is None:
        return None
    if not line[marker.end() :].strip() or looks_like_pem_body_line(following):
        return marker.start()
    return None
