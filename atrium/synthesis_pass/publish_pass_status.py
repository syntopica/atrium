"""Publish the synthesis status file for a finished pass."""

from atrium.state.state_directory import state_directory


def publish_pass_status(
    producer: str,
    started: float,
    finished: float,
    counts: tuple[int, int, int, int, int],
) -> None:
    """``counts`` is (total, made, skipped, failed, deferred)."""
    from atrium.status.publish_json_atomically import publish_json_atomically
    from atrium.status.status_file import status_file
    from atrium.status.synthesis_pass import SynthesisPass
    from atrium.status.synthesis_status import synthesis_status

    publish_json_atomically(
        status_file(state_directory(), "synthesis"),
        synthesis_status(SynthesisPass(producer, started, finished, *counts), finished),
    )
