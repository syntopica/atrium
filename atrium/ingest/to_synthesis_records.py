"""Turn one synthesis-registry record into retrievable index records."""

from collections.abc import Iterator
from typing import Any

from atrium.ingest.record_identity import record_identity
from atrium.record import Record
from atrium.session.redact_sensitive_text import redact_sensitive_text


def to_synthesis_records(record: dict[str, Any], workspace: str | None) -> Iterator[Record]:
    """Yield one index record per synthesized episode.

    The index-side conversation id is namespaced (`synthesis/<source id>`):
    reconciliation deletes by conversation id alone, so sharing the raw
    conversation's id would make each ingest clobber the other's records.
    ``source_sha256`` is the registry job key -- a citation resolves to the
    immutable registry record, which names the exact source events, revision,
    model and prompt behind it.

    ``workspace`` is the source conversation's, recovered by the caller. It has
    no default: a synthesis record with none is unreachable from a
    project-scoped recall -- the shape every session-start injection asks for --
    and that was the original bug here. Passing ``None`` must be a decision a
    caller writes down, not one it can fall into.

    The text is redacted like a note's: model output paraphrases what the
    transcript held, and 80 served records still carried credential values on
    2026-11-05 although every output surface redacts too.
    """
    output = record.get("output") or {}
    parts = [output.get("title") or "", output.get("summary") or ""]
    parts += output.get("facts") or []
    parts += output.get("open_ends") or []
    text = redact_sensitive_text("\n".join(part for part in parts if part).strip())
    if not text:
        return
    conversation_id = f"synthesis/{record['conversation_id']}"
    yield Record(
        record_id=record_identity(conversation_id, record["episode_id"]),
        event_id=record["episode_id"],
        conversation_id=conversation_id,
        source_sha256=record["job_key"],
        provider="synthesis",
        role="synthesis",
        text=text,
        authored_at=record.get("authored_at"),
        workspace=workspace,
        title=redact_sensitive_text(output["title"]) if output.get("title") else None,
        event_index=0,
    )
