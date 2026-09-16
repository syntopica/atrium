"""Whether a ``user`` transcript record is a person's prompt, not a tool result."""

from typing import Any


def is_user_prompt(record: dict[str, Any]) -> bool:
    """True for a user record whose content is text rather than tool results.

    A tool result is also a ``user`` record, and so is a hook's injected
    context. Only a real prompt counts as new work: the bookkeeping of a
    recording turn must not trigger the next reminder.
    """
    if record.get("type") != "user":
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if not isinstance(content, list):
        return False
    kinds = {part.get("type") for part in content if isinstance(part, dict)}
    return "text" in kinds and "tool_result" not in kinds
