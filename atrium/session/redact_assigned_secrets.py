"""Redact ``key = value`` secrets by key name, as the exporter does."""

import re

_KEYS = (
    "api_key",
    "api-key",
    "apikey",
    "access_token",
    "access-token",
    "auth_token",
    "auth-token",
    "client_secret",
    "client-secret",
    "password",
    "passwd",
)

_PATTERNS = [
    re.compile(
        rf"(\b{re.escape(key)}\b\s*[=:]\s*)[\"']?(?!\[REDACTED:)[^\s,\"'}}]{{8,}}",
        re.IGNORECASE,
    )
    for key in _KEYS
]


def redact_assigned_secrets(text: str) -> str:
    """Replace the value of every assigned secret with ``[REDACTED:secret]``.

    Same keys and same shape as rocket-agents' `redactAssignedSecrets.ts`:
    a value of eight or more non-delimiter characters after ``key =`` or
    ``key:``, optionally quoted.
    """
    for pattern in _PATTERNS:
        text = pattern.sub(r"\g<1>[REDACTED:secret]", text)
    return text
