"""Synthesize every episode of one canonical conversation into the registry."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from atrium.status.iso_utc import iso_utc
from atrium.synthesize.ack_worker_results import ack_worker_results
from atrium.synthesize.empty_synthesis_error import EmptySynthesisError
from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.has_record import has_record
from atrium.synthesize.is_trivial_episode import is_trivial_episode
from atrium.synthesize.job_identity import GENERATOR_VERSION, job_identity
from atrium.synthesize.producer import Producer
from atrium.synthesize.segment_episodes import SEGMENTATION_FINGERPRINT, segment_episodes
from atrium.synthesize.started_marker import started_marker
from atrium.synthesize.synthesis_prompt import PROMPT_SHA256
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION
from atrium.synthesize.synthesize_episode import synthesize_episode
from atrium.synthesize.write_record import write_record


def synthesize_conversation(
    conversation: dict[str, Any],
    producer: Producer,
    model_id: str,
    registry: Path,
    done_episodes: set[str] | None = None,
) -> dict[str, Any]:
    """Synthesize each episode not already in the registry. Returns counts.

    ``trivial`` counts lone harness echoes left unsynthesized on purpose; they
    are neither present nor pending.

    The job key hashes every input and recipe field except the output, so a
    re-run skips finished episodes for free, an interrupted run resumes, and
    two machines producing different outputs for the same key is a detectable
    divergence rather than silent disagreement.
    """
    events = conversation.get("events") or []
    revision = (conversation.get("provenance") or {}).get("contentSha256") or ""
    made = skipped = trivial = 0
    marker = started_marker(registry / "partials", conversation["id"])
    for episode in segment_episodes(events):
        event_ids = [events[i].get("id") or str(i) for i in episode["event_indexes"]]
        episode_id = episode_identity(conversation["id"], event_ids)
        job_key = job_identity(conversation["id"], revision, episode_id, model_id)
        # An episode any population already holds is not re-synthesized: recipe
        # coexistence is for deliberate re-runs, never for a producer switch
        # silently paying the whole corpus again.
        if has_record(registry, job_key) or (done_episodes and episode_id in done_episodes):
            skipped += 1
            continue
        if is_trivial_episode(episode["event_indexes"], events):
            trivial += 1
            continue
        # Marked before the first call and cleared only when every episode is
        # recorded: a pass that stops in between leaves the mark, and the next
        # pass walks this conversation first to reuse what it kept.
        marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker.touch()
        began = time.monotonic()
        result = synthesize_episode(episode, events, producer, registry / "partials", model_id)
        duration_ms = round((time.monotonic() - began) * 1000)
        # Worker results are acked only once the record is on disk: a crash in
        # between leaves them offered, and the next pass's drain acks them.
        worker_results = result.get("worker_results") or []
        output = result["input"]
        if not (output.get("title") or output.get("summary")):
            ack_worker_results(worker_results)
            raise EmptySynthesisError(f"empty synthesis for episode {episode_id}")
        output_json = json.dumps(result["input"], ensure_ascii=False, sort_keys=True)
        write_record(
            registry,
            job_key,
            {
                "job_key": job_key,
                "conversation_id": conversation["id"],
                "source": conversation.get("source"),
                "revision_sha256": revision,
                "episode_id": episode_id,
                "event_ids": event_ids,
                "segmentation": SEGMENTATION_FINGERPRINT,
                "model_requested": model_id,
                "model_resolved": result["model"],
                "prompt_sha256": PROMPT_SHA256,
                "output_schema": OUTPUT_SCHEMA_VERSION,
                "generator": GENERATOR_VERSION,
                "map_chunks": len(episode["chunks"]),
                "usage": result["usage"],
                "authored_at": conversation.get("updatedAt") or conversation.get("startedAt"),
                # When and how long: the wall time of every producer call this
                # episode made, map and reduce together. Outside the job key.
                "synthesized_at": iso_utc(time.time()),
                "duration_ms": duration_ms,
                "output": result["input"],
                "output_sha256": hashlib.sha256(output_json.encode()).hexdigest(),
                # The rule the member ids actually follow, taken from the
                # conversation they were read from -- not from this code's
                # own version. Stamping the constant recorded which build
                # wrote the record, so a pass run against a not-yet-upgraded
                # archive stamped 2 onto schema 1 ids, and the re-key then
                # skipped exactly those records as already current.
                "event_id_schema": conversation.get("schemaVersion", 1),
                **({"worker_results": worker_results} if worker_results else {}),
            },
        )
        ack_worker_results(worker_results)
        made += 1
    marker.unlink(missing_ok=True)
    return {"synthesized": made, "skipped": skipped, "trivial": trivial}
