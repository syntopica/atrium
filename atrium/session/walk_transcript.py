"""Walk transcript lines from an offset: boundary, last model, prompts seen."""

from pathlib import Path

from atrium.session.eligible_transcript_record import eligible_transcript_record
from atrium.session.is_user_prompt import is_user_prompt
from atrium.session.transcript_boundary import TranscriptBoundary


def walk_transcript(
    path: Path, start: int
) -> tuple[TranscriptBoundary | None, str | None, int, int]:
    """Return the last eligible boundary, the last model, the prompt count and the bytes.

    The bytes are those of the eligible records only. A transcript is mostly
    attachments, snapshots and system records: a post-compaction re-read of
    the instruction files alone crossed the reminder limit on a turn that
    held one status answer, so the raw file growth measures nothing.
    """
    boundary = None
    model = None
    prompts = 0
    eligible_bytes = 0
    with path.open("rb") as handle:
        handle.seek(start)
        offset = start
        for line in handle:
            offset += len(line)
            record = eligible_transcript_record(line)
            if record is None:
                continue
            eligible_bytes += len(line)
            if is_user_prompt(record):
                prompts += 1
            uuid = record.get("uuid")
            timestamp = record.get("timestamp")
            if isinstance(uuid, str) and isinstance(timestamp, str):
                boundary = TranscriptBoundary(uuid=uuid, timestamp=timestamp, offset=offset)
            if record["type"] == "assistant":
                found = (record.get("message") or {}).get("model")
                model = found if isinstance(found, str) else model
    return boundary, model, prompts, eligible_bytes
