"""The final result event of a `claude -p --output-format stream-json` run."""

import json
from typing import Any


def claude_stream_result(stdout: str) -> dict[str, Any]:
    """Return the last ``result`` event, or an empty dict when the run printed none."""
    found: dict[str, Any] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            found = event
    return found
