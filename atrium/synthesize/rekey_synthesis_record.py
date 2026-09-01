"""Re-key one synthesis record onto the schema 2 event id rule."""

from typing import Any

from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.event_id_schema import EVENT_ID_SCHEMA
from atrium.synthesize.job_identity import job_identity
from atrium.synthesize.qualify_event_id import qualify_event_id


def rekey_synthesis_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the record as it would have been written under the current rule.

    Only the identities move. The output, its hash, the usage and every recipe
    field are carried through untouched, which is the whole point: the episode
    is the same episode and its synthesis was already paid for.

    Idempotent. A record already on the current schema is returned unchanged,
    so a re-run costs nothing and an interrupted pass can simply be repeated.
    """
    if record.get("event_id_schema") == EVENT_ID_SCHEMA:
        return record

    conversation_id = record["conversation_id"]
    event_ids = [qualify_event_id(conversation_id, event_id) for event_id in record["event_ids"]]
    episode_id = episode_identity(conversation_id, event_ids)
    return {
        **record,
        "event_ids": event_ids,
        "episode_id": episode_id,
        "job_key": job_identity(
            conversation_id,
            record.get("revision_sha256") or "",
            episode_id,
            record["model_requested"],
        ),
        "event_id_schema": EVENT_ID_SCHEMA,
    }
