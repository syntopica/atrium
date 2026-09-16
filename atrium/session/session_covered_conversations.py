"""Conversations the session producer already holds records for."""

from collections.abc import Iterable
from typing import Any

from atrium.session.session_segmentation import SESSION_SEGMENTATION


def session_covered_conversations(records: Iterable[dict[str, Any]]) -> set[str]:
    """Return the conversation ids with at least one session-cut record.

    The batch lanes skip these: the author already recorded the conversation,
    and a cold reader paying for it again would add a second population of
    episodes that never share an id with the first.
    """
    return {
        str(record["conversation_id"])
        for record in records
        if record.get("segmentation") == SESSION_SEGMENTATION and record.get("conversation_id")
    }
