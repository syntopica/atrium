"""Tell whether the text between a BEGIN and an END marker can be a key."""

import re

_HEADER = re.compile(r"(?:Proc-Type|DEK-Info): [A-Za-z0-9,-]+")
_MATERIAL = re.compile(r"[\sA-Za-z0-9+/=\\]*")


def is_private_key_material(text: str) -> bool:
    r"""Whether the text is only base64, whitespace, ``\n`` escapes and RFC 1421 headers.

    A lazy ``.*?`` from BEGIN to END ran from a placeholder marker in prose to an
    END marker 6,861 characters on (2026-11-06), taking the host names between.
    Same rule as scribe's `isPrivateKeyMaterial`.
    """
    return _MATERIAL.fullmatch(_HEADER.sub("", text)) is not None
