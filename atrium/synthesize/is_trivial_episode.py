"""Whether an episode is a lone harness echo that no synthesis can use."""

from typing import Any

from atrium.synthesize.harness_echoes import HARNESS_ECHOES


def is_trivial_episode(event_indexes: list[int], events: list[dict[str, Any]]) -> bool:
    """True for an episode whose only event is a known harness echo.

    A floor, not a fold: merging the echo into its neighbour would change that
    episode's event ids, and so its identity, re-keying and re-paying it.
    """
    if len(event_indexes) != 1:
        return False
    return (events[event_indexes[0]].get("text") or "").strip() in HARNESS_ECHOES
