"""Recognize a tool invocation that the archive rendered as an assistant message."""

import re

# Older Claude Code exports carry each tool_use as `kind: message, role: assistant`
# whose text is `tool: <Name>` and, for some tools, the input on the following
# lines; the tool_result arrives as the next `role: user` message, with no marker
# at all. Newer exports use `tool-call` / `tool-result` kinds, which the role rule
# already drops. Measured 2026-10-14 on the live index: 759,708 such invocations
# and 692,868 results, 78% of raw records and 56% of their text, filed as
# conversation.
_RENDERED_CALL = re.compile(r"tool: [A-Za-z0-9_.:-]+(?:\n|$)")


def is_rendered_tool_call(role: str | None, text: str) -> bool:
    """Return whether an assistant message is a rendered tool invocation."""
    return role == "assistant" and _RENDERED_CALL.match(text) is not None
