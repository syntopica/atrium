"""Whether one assistant content part edited a file or committed."""

from typing import Any

from atrium.session.git_commit_pattern import GIT_COMMIT_PATTERN
from atrium.session.work_tool_names import WORK_TOOL_NAMES


def is_work_tool_use(part: Any) -> bool:
    """True for a file-editing tool call or a Bash call that runs `git commit`.

    A read-only interval (questions, reviews, status checks) is left to the
    batch lanes: forcing a recording turn on it cost more than it kept.
    """
    if not isinstance(part, dict) or part.get("type") != "tool_use":
        return False
    name = part.get("name")
    if name in WORK_TOOL_NAMES:
        return True
    command = (part.get("input") or {}).get("command") if name == "Bash" else None
    return isinstance(command, str) and bool(GIT_COMMIT_PATTERN.search(command))
