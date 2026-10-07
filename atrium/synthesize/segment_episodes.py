"""Cut a conversation into episodes -- `episode-texttiling-v1`, deterministic."""

from typing import Any

from atrium.synthesize.enforce_ceiling import enforce_ceiling
from atrium.synthesize.reset_cuts import reset_cuts
from atrium.synthesize.split_at_cuts import split_at_cuts
from atrium.synthesize.turn_blocks import turn_blocks
from atrium.synthesize.valley_cuts import valley_cuts

SEGMENTATION_FINGERPRINT = "episode-texttiling-v1"


def segment_episodes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return episodes covering all events, each with its map chunks.

    An episode is `{"event_indexes": [...], "chunks": [[...], ...]}`. For
    almost every episode `chunks` is one list equal to `event_indexes`; only
    an episode over the token ceiling is mechanically split into several map
    chunks, which exist for model-context reasons and are never retrieval
    episodes -- the reduce step folds them back into one synthesis.

    Cuts happen at (1) explicit reset markers and (2) TextTiling similarity
    valleys over the human turns whose depth exceeds the session's median
    depth plus one MAD, with at least two human turns between cuts. Only
    human text feeds topic detection, so a tool dump cannot fake a shift.
    """
    blocks = turn_blocks(events)
    if not blocks:
        return []
    cuts = reset_cuts(blocks) | valley_cuts(blocks)
    return [
        {
            "event_indexes": episode,
            "chunks": enforce_ceiling(episode, blocks, events),
        }
        for episode in split_at_cuts(blocks, cuts)
    ]
