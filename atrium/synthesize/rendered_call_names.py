"""The tool names a rendered assistant message invokes, in order."""

import re

_CALL_LINE = re.compile(r"^tool: ([A-Za-z0-9_.:-]+)$", re.MULTILINE)


def rendered_call_names(text: str) -> list[str]:
    """Return each `tool: <Name>` line's name; parallel calls render one per line."""
    return _CALL_LINE.findall(text)
