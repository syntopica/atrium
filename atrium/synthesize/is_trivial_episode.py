"""Whether an episode is a lone harness echo that no synthesis can use."""

from typing import Any

# Measured 2026-10-10 over the registry's 2,468 single-event episodes: these
# echoes alone were 2,213 of them ("Structured output provided successfully"
# 2,126, "[Request interrupted by user]" 87), and each paid a full synthesis
# call to produce a record about the echo. Matched exactly, never by length:
# a short lone message from the operator can still be worth remembering.
_ECHOES = frozenset(
    {
        "Structured output provided successfully",
        "[Request interrupted by user]",
    }
)


def is_trivial_episode(event_indexes: list[int], events: list[dict[str, Any]]) -> bool:
    """True for an episode whose only event is a known harness echo.

    A floor, not a fold: merging the echo into its neighbour would change that
    episode's event ids, and so its identity, re-keying and re-paying it.
    """
    if len(event_indexes) != 1:
        return False
    return (events[event_indexes[0]].get("text") or "").strip() in _ECHOES
