"""Group turn blocks into episodes at the chosen cuts."""

from typing import Any


def split_at_cuts(blocks: list[dict[str, Any]], cuts: set[int]) -> list[list[int]]:
    """Return the event indexes of each episode, starting a new one at every cut."""
    episodes: list[list[int]] = [[]]
    for index, block in enumerate(blocks):
        if index in cuts and episodes[-1]:
            episodes.append([])
        episodes[-1].extend(block["event_indexes"])
    return [episode for episode in episodes if episode]
