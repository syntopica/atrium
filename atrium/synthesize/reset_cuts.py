"""Episode cuts at explicit reset markers."""

from typing import Any


def reset_cuts(blocks: list[dict[str, Any]]) -> set[int]:
    """Return the indexes of every non-first block that carries a reset marker."""
    return {index for index, block in enumerate(blocks) if block["resets"] and index > 0}
