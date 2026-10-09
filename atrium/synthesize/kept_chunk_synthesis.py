"""One producer call's synthesis, from the kept copy or from the producer."""

import contextlib
from pathlib import Path
from typing import Any

from atrium.synthesize.ack_worker_results import ack_worker_results
from atrium.synthesize.keep_partial import keep_partial
from atrium.synthesize.partial_path import partial_path
from atrium.synthesize.producer import Producer
from atrium.synthesize.read_partial import read_partial


def kept_chunk_synthesis(  # noqa: PLR0913 -- one producer call plus where to keep it and whether to ack
    system_text: str,
    user_text: str,
    tool: dict[str, Any],
    *,
    producer: Producer,
    partials: Path,
    model_id: str,
    release: bool,
) -> dict[str, Any]:
    """Return the call's synthesis, kept on disk and its worker slot released.

    A map chunk's result used to stay unacked in the worker until its episode
    reduced, holding one of the queue's ``max_outstanding`` slots while the
    episode waited to submit its next chunk. With twenty episodes each holding
    one, the queue was full and none could submit again: the local lane
    synthesized nothing from 2026-10-08 20:01 on. With ``release`` (a map
    chunk) the kept result is acked at once and returned with no worker results;
    the ack is repeated on every read, because a stop between keeping and
    acking would otherwise leave it holding its slot, and acking twice is
    harmless. Without it (the episode's final call) the worker results are
    returned for the caller to ack once the record is written, as before.
    """
    path = partial_path(partials, model_id, system_text, user_text, tool)
    kept = read_partial(path)
    if kept is not None:
        # Reuse is use: the 30-day prune goes by mtime, and a conversation
        # retrying its reduce every pass must not lose the chunks it reads.
        with contextlib.suppress(OSError):
            path.touch()
    if kept is None:
        kept = producer(system_text, user_text, tool)
        output = kept.get("input") or {}
        # An empty synthesis is retried on a later pass, never kept to be
        # reused forever (the caller raises on it, as it always did).
        if output.get("title") or output.get("summary"):
            keep_partial(path, kept)
    if not release:
        return kept
    ack_worker_results(kept.get("worker_results") or [])
    return {key: value for key, value in kept.items() if key != "worker_results"}
