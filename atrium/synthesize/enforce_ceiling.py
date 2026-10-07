"""Split an over-ceiling episode into map chunks."""

from typing import Any

from atrium.synthesize.token_estimate import token_estimate

_TOKEN_CEILING = 32_000


def enforce_ceiling(
    episode: list[int], blocks: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[list[int]]:
    """Return the episode as one chunk, or as several when it exceeds the token ceiling."""
    if token_estimate(episode, events) <= _TOKEN_CEILING:
        return [episode]
    boundaries = {block["event_indexes"][0] for block in blocks}
    chunks: list[list[int]] = [[]]
    for event_index in episode:
        over = chunks[-1] and token_estimate(chunks[-1], events) > _TOKEN_CEILING
        # Prefer cutting at a human boundary, but a single block bigger than
        # the whole ceiling (one 600k-char paste) must still split -- events
        # stay atomic, blocks do not.
        if over and (
            event_index in boundaries or token_estimate(chunks[-1], events) > 2 * _TOKEN_CEILING
        ):
            chunks.append([])
        chunks[-1].append(event_index)
    return [chunk for chunk in chunks if chunk]
