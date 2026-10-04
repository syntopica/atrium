"""Count a conversation's episodes still to synthesize and those already present."""

from pathlib import Path
from typing import Any

from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.job_identity import job_identity
from atrium.synthesize.segment_episodes import segment_episodes
from atrium.synthesize.synthesis_registry import has_record


def episode_backlog(
    conversation: dict[str, Any], model_id: str, registry: Path, done_episodes: set[str]
) -> dict[str, int]:
    """Return ``{"pending", "present"}`` by the rule synthesize_conversation skips by.

    A pass that stops at a wall reports what it left; counting a conversation
    with nothing left to make as deferred inflated that to the whole archive.
    """
    events = conversation.get("events") or []
    revision = (conversation.get("provenance") or {}).get("contentSha256") or ""
    pending = present = 0
    for episode in segment_episodes(events):
        event_ids = [events[i].get("id") or str(i) for i in episode["event_indexes"]]
        episode_id = episode_identity(conversation["id"], event_ids)
        job_key = job_identity(conversation["id"], revision, episode_id, model_id)
        if episode_id in done_episodes or has_record(registry, job_key):
            present += 1
        else:
            pending += 1
    return {"pending": pending, "present": present}
