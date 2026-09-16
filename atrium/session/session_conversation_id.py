"""The archive's conversation id for a live session, derived before export."""

import hashlib


def session_conversation_id(source: str, session_id: str) -> str:
    r"""Return ``sha256(source \\0 session_id)``, the exporter's formula.

    rocket-agents derives it in `streamJsonlConversationRecord.ts` as
    `hashText(`${artifact.source}\\0${sourceId}`)`, with `sourceId` the
    transcript's session id. Computing it here lets a record written during
    the session join the archived conversation's records with no rekey.
    """
    if not source or not session_id:
        raise ValueError("a session conversation id needs a source and a session id")
    return hashlib.sha256(f"{source}\x00{session_id}".encode()).hexdigest()
