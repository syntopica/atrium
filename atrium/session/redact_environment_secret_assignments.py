"""Redact the value of an environment assignment that holds a credential."""

import re

from atrium.session.is_secret_variable_name import is_secret_variable_name

_ASSIGNMENT = re.compile(
    r"\b(?P<name>[A-Z][A-Z0-9_]*) ?= ?(?P<quote>[\"']?)(?P<value>(?!\[REDACTED:)[^\s\"'`]{8,})"
)


def redact_environment_secret_assignments(text: str) -> str:
    """Replace a token-shaped value whose variable name says it is a credential.

    `export RESEND_API_KEY=...` is a key; `STOP_KEY = "Escape"` is a key binding
    and stays, and a URL is where a credential goes, not one. Same rule as
    scribe's `redactEnvironmentSecretAssignments`.
    """

    def replace(match: re.Match[str]) -> str:
        value = match.group("value")
        has_shape = re.search(r"\d", value) and re.search(r"[A-Za-z]", value)
        if not has_shape or "://" in value or not is_secret_variable_name(match.group("name")):
            return match.group(0)
        return match.group(0)[: -len(value)] + "[REDACTED:secret]"

    return _ASSIGNMENT.sub(replace, text)
