"""Count the file edits and commits one transcript record carries."""

from typing import Any

from atrium.session.is_work_tool_use import is_work_tool_use


def count_work_tool_uses(record: dict[str, Any]) -> int:
    """Number of work tool calls in an assistant record; zero for anything else."""
    if record.get("type") != "assistant":
        return 0
    content = (record.get("message") or {}).get("content")
    if not isinstance(content, list):
        return 0
    return sum(1 for part in content if is_work_tool_use(part))
