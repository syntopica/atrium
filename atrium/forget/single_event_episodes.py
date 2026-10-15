"""Map each single-event synthesis episode to the index record that serves it."""

from collections.abc import Iterable
from typing import Any

from atrium.ingest.record_identity import record_identity


def single_event_episodes(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Return conversation id to {archive event id: synthesis record id}.

    The record id is the one ``to_synthesis_records`` gives the episode, so a
    forget event names exactly the row the index serves, whichever population
    produced it.
    """
    found: dict[str, dict[str, str]] = {}
    for record in records:
        event_ids = record.get("event_ids") or []
        if len(event_ids) != 1:
            continue
        conversation_id = record["conversation_id"]
        found.setdefault(conversation_id, {})[event_ids[0]] = record_identity(
            f"synthesis/{conversation_id}", record["episode_id"]
        )
    return found
