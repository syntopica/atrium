"""Synthesize every episode of one canonical conversation into the registry."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from atrium.synthesize.empty_synthesis_error import EmptySynthesisError
from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.job_identity import GENERATOR_VERSION, job_identity
from atrium.synthesize.segment_episodes import SEGMENTATION_FINGERPRINT, segment_episodes
from atrium.synthesize.synthesis_prompt import PROMPT_SHA256, SYNTHESIS_SYSTEM_TEXT
from atrium.synthesize.synthesis_registry import has_record, write_record
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION, SYNTHESIS_TOOL

# A producer is (system_text, user_text, tool) -> {"input", "model", "usage"},
# plus the deterministic model string that enters the job key. Two exist: the
# Max OAuth lane and the Codex CLI. Their records carry different recipe
# fingerprints and coexist in the registry without mixing.
Producer = Callable[[str, str, dict[str, Any]], dict[str, Any]]


def synthesize_conversation(
    conversation: dict[str, Any],
    producer: Producer,
    model_id: str,
    registry: Path,
    done_episodes: set[str] | None = None,
) -> dict[str, Any]:
    """Synthesize each episode not already in the registry. Returns counts.

    The job key hashes every input and recipe field except the output, so a
    re-run skips finished episodes for free, an interrupted run resumes, and
    two machines producing different outputs for the same key is a detectable
    divergence rather than silent disagreement.
    """
    events = conversation.get("events") or []
    revision = (conversation.get("provenance") or {}).get("contentSha256") or ""
    made = skipped = 0
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
        result = _synthesize_episode(episode, events, producer)
        output = result["input"]
        if not (output.get("title") or output.get("summary")):
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
                "output": result["input"],
                "output_sha256": hashlib.sha256(output_json.encode()).hexdigest(),
                # The rule the member ids actually follow, taken from the
                # conversation they were read from -- not from this code's
                # own version. Stamping the constant recorded which build
                # wrote the record, so a pass run against a not-yet-upgraded
                # archive stamped 2 onto schema 1 ids, and the re-key then
                # skipped exactly those records as already current.
                "event_id_schema": conversation.get("schemaVersion", 1),
            },
        )
        made += 1
    return {"synthesized": made, "skipped": skipped}


def _synthesize_episode(
    episode: dict[str, Any], events: list[dict[str, Any]], producer: Producer
) -> dict[str, Any]:
    chunks = episode["chunks"]
    if len(chunks) == 1:
        return producer(SYNTHESIS_SYSTEM_TEXT, _transcript(chunks[0], events), SYNTHESIS_TOOL)
    # Map-reduce for the long tail: chunk syntheses exist only to fit model
    # context and are folded back into exactly one episode record.
    partials = [
        producer(SYNTHESIS_SYSTEM_TEXT, _transcript(chunk, events), SYNTHESIS_TOOL)
        for chunk in chunks
    ]
    reduce_input = "\n\n".join(
        f"[part {index + 1}]\n{json.dumps(partial['input'], ensure_ascii=False)}"
        for index, partial in enumerate(partials)
    )
    reduced = producer(
        SYNTHESIS_SYSTEM_TEXT
        + "\nThe user message holds partial syntheses of consecutive parts of ONE "
        "episode. Merge them into a single faithful synthesis of the whole episode.",
        reduce_input,
        SYNTHESIS_TOOL,
    )
    reduced["usage"] = {
        "input_tokens": sum(p["usage"].get("input_tokens", 0) for p in [*partials, reduced]),
        "output_tokens": sum(p["usage"].get("output_tokens", 0) for p in [*partials, reduced]),
    }
    return reduced


# One event's contribution to a synthesis transcript. A single 600k-character
# paste is mostly logs; synthesis needs its head and tail, and the verbatim
# body stays in the canonical archive the record cites.
_EVENT_CHAR_CAP = 60_000


def _transcript(event_indexes: list[int], events: list[dict[str, Any]]) -> str:
    lines = []
    for index in event_indexes:
        event = events[index]
        text = (event.get("text") or "").strip()
        if len(text) > _EVENT_CHAR_CAP:
            half = _EVENT_CHAR_CAP // 2
            text = f"{text[:half]}\n[... truncated for synthesis ...]\n{text[-half:]}"
        if text:
            lines.append(f"[{event.get('role', 'unknown')}] {text}")
    return "\n".join(lines)
