"""Re-key one archive event id onto the schema 2 rule."""

import hashlib


def qualify_event_id(conversation_id: str, event_id: str) -> str:
    """Return the schema 2 id of an event that carried ``event_id`` under schema 1.

    Rocket Agents changed the rule in `0f7217d`: an id derived from event index
    and text alone collided across conversations, so it now binds the
    conversation into the hash. The upgrade is a pure function of the old id,
    which is the only reason this registry can be re-keyed at all -- the
    alternative would be re-synthesizing 16,148 episodes and paying the model
    quota for work already done.

    It must stay byte-identical to `qualifyConversationEventIds.ts`, which
    hashes `conversation_id NUL old_id` with SHA-256 and renders it as hex.
    """
    if not conversation_id or not event_id:
        raise ValueError("qualifying an event id needs both a conversation id and an event id")
    return hashlib.sha256(f"{conversation_id}\x00{event_id}".encode()).hexdigest()
