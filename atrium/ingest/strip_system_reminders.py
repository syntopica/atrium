"""Remove harness-injected <system-reminder> blocks from a user message."""

import re

# A closed pair only: an unterminated tag matches nothing, so person text after it survives.
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def strip_system_reminders(role: str | None, text: str) -> str:
    """Return a user message without its reminder blocks, trimmed; other roles pass through."""
    if role != "user":
        return text
    return _REMINDER.sub("", text).strip()
