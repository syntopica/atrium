"""Which events of a conversation are tool traffic rather than conversation."""

from collections import deque
from typing import Any

from atrium.ingest.tool_round import ToolRound
from atrium.synthesize.document_tools import DOCUMENT_TOOLS
from atrium.synthesize.rendered_call_names import rendered_call_names

_CONVERSATION_ROLES = frozenset({"user", "assistant"})


def tool_output_indexes(events: list[dict[str, Any]]) -> set[int]:
    """Return the indexes of tool calls, tool results and harness messages.

    A role other than user or assistant is tool or harness text: tool results,
    Codex `exec` calls and their output (no role at all), developer and system
    instructions. Older Claude Code exports render calls as assistant messages
    and results as user messages; `ToolRound` pairs those, so a rendered result
    is not mistaken for the human's turn. Results answer calls in call order,
    so the result of a document tool (`DOCUMENT_TOOLS`) is left out.
    """
    round_ = ToolRound()
    owed: deque[str] = deque()
    indexes = set()
    for index, event in enumerate(events):
        role = event.get("role")
        text = event.get("text") or ""
        rule = round_.classify(role, event.get("kind"), text)
        if rule == "rendered tool call":
            owed.extend(rendered_call_names(text))
        is_result = rule == "rendered tool result" or role == "tool"
        answers = owed.popleft() if is_result and owed else None
        if answers in DOCUMENT_TOOLS:
            continue
        if rule is not None or role not in _CONVERSATION_ROLES:
            indexes.add(index)
    return indexes
