"""Replace each private key written inline between its BEGIN and END markers."""

import re

from atrium.session.is_private_key_material import is_private_key_material
from atrium.session.leading_key_material_length import leading_key_material_length
from atrium.session.redact_key_material_runs import redact_key_material_runs

_BEGIN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
_END = re.compile(r"-----END [A-Z0-9 ]*PRIVATE KEY-----")
_MARKER = "[REDACTED:private-key]"


def redact_inline_private_keys(text: str) -> str:
    """Pair each BEGIN with the next END and redact the key between, failing closed.

    When only key material lies between the whole key goes; otherwise, and when
    no END follows, the key runs after the marker go and the prose stays. Same
    rule as scribe's `redactInlinePrivateKeys`.
    """
    position = 0
    while (begin := _BEGIN.search(text, position)) is not None:
        body = begin.end()
        end = _END.search(text, body)
        if end is not None and is_private_key_material(text[body : end.start()]):
            text = text[: begin.start()] + _MARKER + text[end.end() :]
            position = begin.start() + len(_MARKER)
            continue
        stop = body + leading_key_material_length(text[body:]) if end is None else end.start()
        runs = redact_key_material_runs(text[body:stop])
        text = text[:body] + runs + text[stop:]
        position = body + len(runs)
    return text
