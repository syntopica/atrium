"""Pair rendered tool invocations with the unmarked results that answer them."""

from dataclasses import dataclass

from atrium.ingest.is_rendered_tool_call import is_rendered_tool_call

_RESULT_KINDS = frozenset({"tool-result", "tool_result"})


@dataclass
class ToolRound:
    """Results still owed to rendered tool calls within one conversation.

    Parallel calls render as a run of invocations followed by a run of results,
    so a count, not a flag, is what keeps the user's next real prompt from being
    taken for a result.
    """

    pending: int = 0

    def classify(self, role: str | None, kind: str | None, text: str) -> str | None:
        """Return the rejection rule for a rendered call or result, else None."""
        if self.pending and (role == "tool" or kind in _RESULT_KINDS):
            # Since scribe 199f393 a new result carries its own role; the role
            # rule drops it, but it still settles the call it answers.
            self.pending -= 1
            return None
        if kind != "message":
            return None
        if is_rendered_tool_call(role, text):
            self.pending += 1
            return "rendered tool call"
        if role == "user" and self.pending:
            self.pending -= 1
            return "rendered tool result"
        if role == "assistant":
            # Prose closes the round: a result that never arrived must not
            # swallow the next prompt.
            self.pending = 0
        return None
