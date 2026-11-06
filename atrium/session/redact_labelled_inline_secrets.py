"""Redact the value of an inline ``Label: value`` credential, outside any table."""

import re

from atrium.session.is_inline_secret_label import is_inline_secret_label

# A label of up to five words, a colon, then a token-shaped value, optionally
# quoted or backticked. The label starts after a line start or a delimiter.
_INLINE = re.compile(
    r"(?P<label>(?<![\w])[A-Za-z][\w.()-]*(?:[ _][\w.()-]+){0,4})\s*:\s*"
    r"(?P<quote>[`'\"]?)(?P<value>(?!\[REDACTED:)[A-Za-z0-9_\-+/=.]{16,})(?P=quote)"
)


def redact_labelled_inline_secrets(text: str) -> str:
    """Replace the value when the label names a credential and the value has letters and digits.

    Curated notes keep credentials as bullets ("- Client secret: `...`",
    "Token API Hetzner Cloud: ..."), which the table rule never sees; this
    reached context output until 2026-11-06. A value without both letters and
    digits is prose, not a token, and stays.
    """

    def replace(match: re.Match[str]) -> str:
        value = match.group("value")
        label = re.split(r"[|*•;,/]| - ", match.group("label"))[-1].strip()
        has_shape = re.search(r"\d", value) and re.search(r"[A-Za-z]", value)
        if not has_shape or not is_inline_secret_label(label):
            return match.group(0)
        start = match.start("value") - match.start(0)
        end = match.end("value") - match.start(0)
        whole = match.group(0)
        return whole[:start] + "[REDACTED:secret]" + whole[end:]

    return _INLINE.sub(replace, text)
