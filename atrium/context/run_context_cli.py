"""JSON command-line rendering of the shared context contract."""

import json
from pathlib import Path

from atrium.context.context_from_index import context_from_index


def run_context_cli(  # noqa: PLR0913, PLR0917 -- parser wiring
    index: Path,
    query: str,
    project: Path | None,
    limit: int,
    max_chars: int,
    lane: str,
    state: Path,
) -> int:
    """Write structured output even when the selected store is unavailable."""
    result = context_from_index(
        index, query, project=project, limit=limit, max_chars=max_chars, lane=lane, state=state
    )
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["index_status"] == "unavailable" else 0
