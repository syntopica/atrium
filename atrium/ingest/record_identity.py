"""Derive a globally unique, deterministic identity for a record."""

import hashlib


def record_identity(conversation_id: str, event_id: str) -> str:
    """Return the primary key for one event inside one conversation.

    The archive's event id is NOT unique on its own: rocket-agents derives it
    from the event index and text alone, with no conversation or provider in the
    hash, so the same sentence at the same position in two conversations
    produces the same id. Measured on real exports, using it directly as a
    primary key silently lost 17 of 2,586 OpenCode records and 73 of 67,568
    Cursor records -- and worse, the surviving row mixed one conversation's
    identity with another's revision hash, so it could cite neither.

    Hashing the pair keeps the property that matters -- two machines ingesting
    the same archive derive the same key without coordinating -- while making
    the key unique.
    """
    if not conversation_id or not event_id:
        raise ValueError("record identity needs both a conversation id and an event id")
    return hashlib.sha256(f"{conversation_id}\x00{event_id}".encode()).hexdigest()
