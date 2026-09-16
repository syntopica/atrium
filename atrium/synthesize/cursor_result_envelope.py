"""The result envelope cursor-agent prints in JSON output mode, or None."""

import json
from typing import Any, cast


def cursor_result_envelope(stdout: str) -> dict[str, Any] | None:
    """Return the ``{"type": "result", ...}`` object on stdout, or None.

    Read from the last line backwards: the envelope is the final thing the
    CLI prints, and anything before it is noise this lane does not parse. An
    empty stdout, the shape an oversized prompt produces with exit 0, is
    reported as the envelope's absence rather than as a model that declined.
    """
    for line in reversed(stdout.strip().splitlines()):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("type") == "result":
            return cast("dict[str, Any]", parsed)
    return None
