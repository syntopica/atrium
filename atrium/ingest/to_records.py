"""Turn one canonical conversation into retrievable records."""

from collections.abc import Iterator

from atrium.record import Record

# Roles that carry conversation. Everything else in an archive event stream is
# machinery: tool invocations, system notices, and provider-specific chrome. The
# system this replaces indexed all of it and paid for it -- 251,568 drawers of
# serialized tool output, 18.8% of the whole index, competing with prose in every
# search.
CONVERSATIONAL_ROLES = frozenset({"user", "assistant"})

# An event shorter than this carries no retrievable claim. Measured on the
# previous index: 101,967 records (7.6%) were under this length, and they are
# acknowledgements -- "ok", "adelante", "gracias".
MIN_TEXT_LENGTH = 120


def to_records(conversation: dict) -> Iterator[Record]:
    """Yield one record per conversational event worth retrieving.

    Skips non-conversational events and acknowledgements. Nothing is deleted by
    skipping: the archive keeps every event, and this only decides what earns a
    row in a derived index that can be rebuilt with a different rule tomorrow.
    """
    conversation_id = conversation.get("id")
    provenance = conversation.get("provenance") or {}
    source_sha256 = provenance.get("contentSha256")
    if not conversation_id or not source_sha256:
        raise ValueError("conversation lacks id or provenance.contentSha256")

    provider = conversation.get("source") or "unknown"
    workspace = conversation.get("workspace")
    title = conversation.get("title")

    for index, event in enumerate(conversation.get("events") or []):
        if event.get("kind") != "message":
            continue
        if event.get("role") not in CONVERSATIONAL_ROLES:
            continue
        text = (event.get("text") or "").strip()
        if len(text) < MIN_TEXT_LENGTH:
            continue
        event_id = event.get("id")
        if not event_id:
            continue
        yield Record(
            record_id=event_id,
            conversation_id=conversation_id,
            source_sha256=source_sha256,
            provider=provider,
            role=event["role"],
            text=text,
            authored_at=event.get("timestamp") or conversation.get("startedAt"),
            workspace=workspace,
            title=title,
            event_index=index,
        )
