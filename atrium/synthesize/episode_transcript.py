"""The transcript text one synthesis call reads."""

from typing import Any

from atrium.synthesize.head_and_tail import head_and_tail
from atrium.synthesize.tool_output_char_cap import TOOL_OUTPUT_CHAR_CAP
from atrium.synthesize.tool_output_indexes import tool_output_indexes

# One event's contribution to a synthesis transcript. A single 600k-character
# paste is mostly logs; synthesis needs its head and tail, and the verbatim
# body stays in the canonical archive the record cites.
_EVENT_CHAR_CAP = 60_000


def episode_transcript(event_indexes: list[int], events: list[dict[str, Any]]) -> str:
    """Render the given events as role-tagged lines, capping each event's text.

    Tool traffic gets the tighter cap: segmentation still counts the full text,
    so episodes and their map chunks do not move, only what each call reads.
    """
    tool = tool_output_indexes(events)
    lines = []
    for index in event_indexes:
        event = events[index]
        cap = TOOL_OUTPUT_CHAR_CAP if index in tool else _EVENT_CHAR_CAP
        text = head_and_tail((event.get("text") or "").strip(), cap)
        if text:
            lines.append(f"[{event.get('role', 'unknown')}] {text}")
    return "\n".join(lines)
