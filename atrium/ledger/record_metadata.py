"""Describe one synthesis record by identities, recipe and cost, never content."""

from typing import Any

from atrium.ledger.record_tokens import record_tokens
from atrium.session.session_segmentation import SESSION_SEGMENTATION
from atrium.status.iso_utc import iso_utc


def record_metadata(record: dict[str, Any], written_at: float) -> dict[str, Any]:
    """Return what a status reader may store: ids, model, tokens, counts.

    The output's title, summary, facts and open ends are content: only their
    counts appear here. ``synthesis show`` is the one reader of the text.
    """
    raw_output, raw_session = record.get("output"), record.get("session")
    output: dict[str, Any] = raw_output if isinstance(raw_output, dict) else {}
    session: dict[str, Any] | None = raw_session if isinstance(raw_session, dict) else None
    input_tokens, output_tokens = record_tokens(record)
    duration = record.get("duration_ms")
    return {
        "jobKey": record.get("job_key"),
        "kind": "session" if record.get("segmentation") == SESSION_SEGMENTATION else "episode",
        "source": record.get("source"),
        "conversationId": record.get("conversation_id"),
        "episodeId": record.get("episode_id"),
        "eventCount": len(record.get("event_ids") or []),
        "session": None
        if session is None
        else {"since": session.get("since"), "until": session.get("until")},
        "authoredAt": record.get("authored_at"),
        "writtenAt": iso_utc(written_at),
        "modelRequested": record.get("model_requested"),
        "modelResolved": record.get("model_resolved"),
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "durationMs": duration if isinstance(duration, int) and duration >= 0 else None,
        "mapChunks": record.get("map_chunks"),
        "workerResults": len(record.get("worker_results") or []),
        "facts": len(output.get("facts") or []),
        "openEnds": len(output.get("open_ends") or []),
    }
