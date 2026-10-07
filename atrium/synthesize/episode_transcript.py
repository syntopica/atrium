"""The transcript text one synthesis call reads."""

from typing import Any

# One event's contribution to a synthesis transcript. A single 600k-character
# paste is mostly logs; synthesis needs its head and tail, and the verbatim
# body stays in the canonical archive the record cites.
_EVENT_CHAR_CAP = 60_000


def episode_transcript(event_indexes: list[int], events: list[dict[str, Any]]) -> str:
    """Render the given events as role-tagged lines, capping each event's text."""
    lines = []
    for index in event_indexes:
        event = events[index]
        text = (event.get("text") or "").strip()
        if len(text) > _EVENT_CHAR_CAP:
            half = _EVENT_CHAR_CAP // 2
            text = f"{text[:half]}\n[... truncated for synthesis ...]\n{text[-half:]}"
        if text:
            lines.append(f"[{event.get('role', 'unknown')}] {text}")
    return "\n".join(lines)
