"""Run a pass step on a conversation loaded only when its turn comes."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from atrium.synthesis_pass.conversation_at import conversation_at


def run_loaded(
    run_one: Callable[[tuple[int, dict[str, Any]]], dict[str, int]],
    archive: Path,
    item: tuple[int, dict[str, Any]],
) -> dict[str, int]:
    """Load ``item``'s stub from the archive, then hand it to ``run_one``.

    ``ThreadPoolExecutor.map`` takes every argument up front, so loading here,
    inside the worker thread, is what keeps only the conversations in flight
    in memory.
    """
    position, stub = item
    return run_one((position, conversation_at(archive, stub["offset"])))
