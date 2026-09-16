"""The archive's redaction policy, applied to a record before it is written."""

import re

from atrium.session.redact_assigned_secrets import redact_assigned_secrets
from atrium.session.redact_private_key_blocks import redact_private_key_blocks

_TOKEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bBearer\s+(?!\[REDACTED:)\S{16,}", re.IGNORECASE), "Bearer [REDACTED:token]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED:aws-access-key]"),
    (re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{20,}\b"), "[REDACTED:token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED:token]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED:token]"),
    (
        re.compile(r"(https?://)(?!\[REDACTED:)[^\s@]+@", re.IGNORECASE),
        r"\g<1>[REDACTED:credentials]@",
    ),
]


def redact_sensitive_text(text: str) -> str:
    """Return ``text`` with keys, assigned secrets and known tokens redacted.

    A session record is written from the model's own words, not from the
    archive, so it would otherwise bypass the exporter's `redactSensitiveText`
    and index a credential verbatim. Same patterns, same order, same markers.
    """
    text = redact_private_key_blocks(text)
    text = redact_assigned_secrets(text)
    for pattern, replacement in _TOKEN_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
