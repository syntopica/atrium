"""Recognize a user-role message that a harness or an app wrote."""

import re

from atrium.ingest.machine_prompt_prefixes import MACHINE_PROMPT_PREFIXES

_WHITESPACE = re.compile(r"\s+")


def is_machine_prompt(role: str | None, text: str) -> bool:
    """Return whether a user message opens with a known machine-written prompt."""
    if role != "user":
        return False
    # Collapsed so "<role>\nYou are" matches the same opening as "<role> You are".
    opening = _WHITESPACE.sub(" ", text[:160]).strip()
    return opening.startswith(MACHINE_PROMPT_PREFIXES)
