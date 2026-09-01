"""Group a conversation's events into human-anchored turn blocks."""

import re
from typing import Any

# A human message that resets context ends an episode unconditionally.
_RESET = re.compile(r"^\s*(?:/clear|/reset|/compact)\b", re.IGNORECASE)


def turn_blocks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return turn blocks: each human message plus everything until the next.

    The block is the segmentation unit of `episode-texttiling-v1`: topic
    detection looks only at the human turns, so long assistant or tool dumps
    cannot masquerade as topic shifts, but every event still belongs to exactly
    one block and therefore to exactly one episode. Events before the first
    human message ride with the first block.
    """
    blocks: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if event.get("kind") != "message":
            continue
        text = (event.get("text") or "").strip()
        if event.get("role") == "user":
            blocks.append(
                {
                    "human_text": text,
                    "event_indexes": [index],
                    "resets": bool(_RESET.match(text)),
                }
            )
        elif blocks:
            blocks[-1]["event_indexes"].append(index)
        else:
            blocks.append({"human_text": "", "event_indexes": [index], "resets": False})
    return blocks
