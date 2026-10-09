"""One episode's synthesis, folded into a single record."""

import functools
import json
from pathlib import Path
from typing import Any

from atrium.synthesize.episode_transcript import episode_transcript
from atrium.synthesize.kept_chunk_synthesis import kept_chunk_synthesis
from atrium.synthesize.producer import Producer
from atrium.synthesize.synthesis_prompt import SYNTHESIS_SYSTEM_TEXT
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL


def synthesize_episode(
    episode: dict[str, Any],
    events: list[dict[str, Any]],
    producer: Producer,
    partials: Path | None = None,
    model_id: str = "",
) -> dict[str, Any]:
    """Synthesize one episode, map-reducing it when it spans several chunks.

    With ``partials`` every producer call is kept on disk, so an identical call
    from another conversation reuses the file instead of the worker key. Map
    chunks are acked at once to free their worker slots; the final call's
    results go back to the caller, which acks them after writing the record.
    """
    final: Producer = producer
    chunk: Producer = producer
    if partials is not None:
        kept = functools.partial(
            kept_chunk_synthesis, producer=producer, partials=partials, model_id=model_id
        )
        final = functools.partial(kept, release=False)
        chunk = functools.partial(kept, release=True)
    chunks = episode["chunks"]
    if len(chunks) == 1:
        return final(SYNTHESIS_SYSTEM_TEXT, episode_transcript(chunks[0], events), SYNTHESIS_TOOL)
    # Map-reduce for the long tail: chunk syntheses exist only to fit model
    # context and are folded back into exactly one episode record.
    mapped = [
        chunk(SYNTHESIS_SYSTEM_TEXT, episode_transcript(part, events), SYNTHESIS_TOOL)
        for part in chunks
    ]
    reduce_input = "\n\n".join(
        f"[part {index + 1}]\n{json.dumps(partial['input'], ensure_ascii=False)}"
        for index, partial in enumerate(mapped)
    )
    reduced = final(
        SYNTHESIS_SYSTEM_TEXT
        + "\nThe user message holds partial syntheses of consecutive parts of ONE "
        "episode. Merge them into a single faithful synthesis of the whole episode.",
        reduce_input,
        SYNTHESIS_TOOL,
    )
    reduced["usage"] = {
        "input_tokens": sum(p["usage"].get("input_tokens", 0) for p in [*mapped, reduced]),
        "output_tokens": sum(p["usage"].get("output_tokens", 0) for p in [*mapped, reduced]),
    }
    reduced["worker_results"] = [
        r for p in [*mapped, reduced] for r in p.get("worker_results") or []
    ]
    return reduced
