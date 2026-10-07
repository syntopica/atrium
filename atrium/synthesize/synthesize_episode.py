"""One episode's synthesis, folded into a single record."""

import json
from typing import Any

from atrium.synthesize.episode_transcript import episode_transcript
from atrium.synthesize.producer import Producer
from atrium.synthesize.synthesis_prompt import SYNTHESIS_SYSTEM_TEXT
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL


def synthesize_episode(
    episode: dict[str, Any], events: list[dict[str, Any]], producer: Producer
) -> dict[str, Any]:
    """Synthesize one episode, map-reducing it when it spans several chunks."""
    chunks = episode["chunks"]
    if len(chunks) == 1:
        return producer(
            SYNTHESIS_SYSTEM_TEXT, episode_transcript(chunks[0], events), SYNTHESIS_TOOL
        )
    # Map-reduce for the long tail: chunk syntheses exist only to fit model
    # context and are folded back into exactly one episode record.
    partials = [
        producer(SYNTHESIS_SYSTEM_TEXT, episode_transcript(chunk, events), SYNTHESIS_TOOL)
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
    reduced["worker_results"] = [
        r for p in [*partials, reduced] for r in p.get("worker_results") or []
    ]
    return reduced
