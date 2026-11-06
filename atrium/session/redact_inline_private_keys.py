"""Replace each private key written inline between its BEGIN and END markers."""

import re

from atrium.session.is_private_key_material import is_private_key_material

_BEGIN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
_END = re.compile(r"-----END [A-Z0-9 ]*PRIVATE KEY-----")
_MARKER = "[REDACTED:private-key]"


def redact_inline_private_keys(text: str) -> str:
    """Pair each BEGIN with the next END when only key material lies between.

    A BEGIN that fails is skipped, so a real key after it is still found. Same
    rule as scribe's `redactInlinePrivateKeys`.
    """
    position = 0
    while (begin := _BEGIN.search(text, position)) is not None:
        end = _END.search(text, begin.end())
        if end is None:
            break
        if not is_private_key_material(text[begin.end() : end.start()]):
            position = begin.end()
            continue
        text = text[: begin.start()] + _MARKER + text[end.end() :]
        position = begin.start() + len(_MARKER)
    return text
