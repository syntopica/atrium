"""Emit the file-history hook result without replacing the tool output."""

import contextlib
import json
import sys

from file_history import file_history


def main() -> None:
    """Deliver additional context for a supported completed tool call."""
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != "PostToolUse" or not payload.get("session_id"):
        return
    context = file_history(payload)
    if context:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": context,
                }
            },
            sys.stdout,
        )


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
