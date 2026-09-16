"""Identity of one session-cut episode: its transcript boundary."""

import hashlib

from atrium.session.session_segmentation import SESSION_SEGMENTATION


def session_episode_identity(conversation_id: str, boundary_uuid: str) -> str:
    """Hash of the cutter, the conversation and the boundary record's uuid.

    The boundary is the last eligible transcript record when the checkpoint
    was frozen, so a retry of the same checkpoint names the same episode and
    the recording tool call's own records never move it.
    """
    if not conversation_id or not boundary_uuid:
        raise ValueError("a session episode needs a conversation id and a boundary uuid")
    payload = "\x00".join([SESSION_SEGMENTATION, conversation_id, boundary_uuid])
    return hashlib.sha256(payload.encode()).hexdigest()[:24]
