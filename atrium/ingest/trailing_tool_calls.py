"""Count the tool invocations rendered at the end of an assistant prose message."""

import re

# Claude Code also renders a call on the message that announces it: "Reading the
# deploy script.\ntool: Read". The prose is worth keeping; the result that
# follows is not. Measured 2026-10-14 on 3,000 conversations: 16 such messages,
# every one followed by its result filed as a user message.
_TRAILING_CALLS = re.compile(r"(?:\ntool: [A-Za-z0-9_.:-]+)+\s*$")


def trailing_tool_calls(text: str) -> int:
    """Return how many rendered invocations close ``text``."""
    found = _TRAILING_CALLS.search(text)
    return found.group().count("\ntool: ") if found else 0
