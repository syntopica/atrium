"""Redact ``key = value`` secrets by key name, as the exporter does."""

import re

from atrium.session.assigned_secret_keys import ASSIGNED_SECRET_KEYS
from atrium.session.is_non_secret_value import is_non_secret_value

_PATTERNS = [
    re.compile(
        rf"(\b{re.escape(key)}\b\s*[=:]\s*)[\"']?(?P<value>(?!\[REDACTED:)[^\s,\"'}}]{{8,}})",
        re.IGNORECASE,
    )
    for key in ASSIGNED_SECRET_KEYS
]


def redact_assigned_secrets(text: str) -> str:
    """Replace the value of every assigned secret with ``[REDACTED:secret]``.

    Same keys and same shape as scribe's `redactAssignedSecrets.ts`: a value of
    eight or more non-delimiter characters after ``key =`` or ``key:``,
    optionally quoted, unless `is_non_secret_value` says it is not a credential.
    """

    def replace(match: re.Match[str]) -> str:
        if is_non_secret_value(match.group("value")):
            return match.group(0)
        return match.group(1) + "[REDACTED:secret]"

    for pattern in _PATTERNS:
        text = pattern.sub(replace, text)
    return text
