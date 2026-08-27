"""Derive the deterministic identity of one episode."""

import hashlib

from atrium.synthesize.segment_episodes import SEGMENTATION_FINGERPRINT


def episode_identity(conversation_id: str, event_ids: list[str]) -> str:
    """Hash of the conversation, the ordered member events, and the cutter.

    Two machines segmenting the same conversation revision with the same
    cutter derive the same episode ids without coordinating -- the property
    every other identity in this system already has. A cutter change changes
    the fingerprint and therefore every episode id, which is correct: those
    are different episodes.
    """
    if not conversation_id or not event_ids:
        raise ValueError("episode identity needs a conversation id and member events")
    payload = "\x00".join([SEGMENTATION_FINGERPRINT, conversation_id, *event_ids])
    return hashlib.sha256(payload.encode()).hexdigest()[:24]
