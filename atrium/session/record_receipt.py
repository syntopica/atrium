"""What `record-session` prints: the accepted record, for the transcript to keep."""

from typing import Any


def record_receipt(record: dict[str, Any], existed: bool) -> dict[str, Any]:
    """The receipt's tool result carries the judgment into the archive.

    A Bash command's text is not exported (`input.command` is not a text
    key), so the JSON the model wrote would otherwise exist only in the
    registry; printing the accepted record makes it replayable from layer 1.
    """
    return {
        "recorded": "already" if existed else "new",
        "job_key": record["job_key"],
        "conversation_id": record["conversation_id"],
        "episode_id": record["episode_id"],
        "model_requested": record["model_requested"],
        "session": record["session"],
        "output": record["output"],
    }
