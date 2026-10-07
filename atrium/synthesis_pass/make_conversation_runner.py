"""Build the per-conversation step a worker pool maps over."""

import functools
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane
from atrium.synthesis_pass.registry_state import RegistryState
from atrium.synthesize.default_registry import default_registry
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.record_worker_submission import record_worker_submission


def make_conversation_runner(
    lane: ProducerLane,
    state: RegistryState,
    holding: set[str],
    journal: Path,
    total: int,
) -> Callable[[tuple[int, dict[str, Any]]], dict[str, int]]:
    """Return a step mapping (position, conversation) to its outcome counts."""
    # Once the quota window is spent (or the worker's queue is full, or every
    # runner rests) nothing left in the pass can succeed: stop calling, count
    # the rest as deferred -- still pending, not failed -- and let a later tick
    # pick them up instead of grinding failures.
    quota_wall = threading.Event()

    def run_one(item: tuple[int, dict[str, Any]]) -> dict[str, int]:
        from atrium.synthesize.synthesize_conversation import synthesize_conversation

        position, conversation = item
        collecting = conversation["id"] in holding
        walled = quota_wall.is_set() and not collecting
        revision = (conversation.get("provenance") or {}).get("contentSha256") or ""
        # After a wall, a conversation already synthesized at its current
        # revision is present, not deferred: deferred means work left undone.
        if conversation["id"] in state.covered or (
            walled and (conversation["id"], revision) in state.recorded_revisions
        ):
            # Covered: the session that lived it already recorded it.
            return {"synthesized": 0, "skipped": 1, "failed": 0}
        if walled:
            return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
        producer_call = lane.call
        if lane.worker_queue is not None and lane.journaled_call is not None:
            on_submit = functools.partial(
                record_worker_submission, journal, conversation_id=conversation["id"]
            )
            producer_call = functools.partial(lane.journaled_call, on_submit=on_submit)
        try:
            result = synthesize_conversation(
                conversation, producer_call, lane.model_id, default_registry(), state.done_episodes
            )
        except QuotaExhaustedError as error:
            if collecting:
                # Only this conversation's new chunk was refused: the others
                # holding results are walked next and must not be stranded.
                print(f"  [{position}/{total}] queue full while collecting: {error}", flush=True)
                return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
            if not quota_wall.is_set():
                quota_wall.set()
                print(f"  [{position}/{total}] quota wall, aborting pass: {error}", flush=True)
            return {"synthesized": 0, "skipped": 0, "failed": 0, "deferred": 1}
        except Exception as error:
            print(f"  [{position}/{total}] {conversation['id'][:12]} FAILED: {error}", flush=True)
            return {"synthesized": 0, "skipped": 0, "failed": 1}
        print(
            f"  [{position}/{total}] {conversation['id'][:12]} "
            f"+{result['synthesized']} (skipped {result['skipped']})",
            flush=True,
        )
        return {**result, "failed": 0}

    return run_one
