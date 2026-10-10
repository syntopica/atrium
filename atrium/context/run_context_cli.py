"""JSON command-line rendering of the shared context contract."""

import json
from pathlib import Path

from atrium.context.context_from_index import context_from_index
from atrium.serve.context_socket_path import context_socket_path
from atrium.serve.request_context_service import request_context_service
from atrium.serve.service_timeout_response import service_timeout_response

# Below the prompt hook's 10 s kill, leaving room for interpreter startup: a
# late answer is discarded by the hook anyway, an explicit timeout is not.
_SERVICE_TIMEOUT_S = 7.0


def run_context_cli(  # noqa: PLR0913, PLR0917 -- parser wiring
    index: Path,
    query: str,
    project: Path | None,
    limit: int,
    max_chars: int,
    lane: str,
    state: Path,
) -> int:
    """Ask the resident service first, retrieve in-process only without one.

    Writes structured output even when the selected store is unavailable.
    """
    request = {
        "index": str(index),
        "query": query,
        "project": str(project) if project is not None else None,
        "limit": limit,
        "max_chars": max_chars,
        "lane": lane,
        "state": str(state),
    }
    try:
        result = request_context_service(context_socket_path(state), request, _SERVICE_TIMEOUT_S)
    except TimeoutError:
        result = service_timeout_response(query, project, limit, max_chars, lane, state)
    except (OSError, ValueError):
        result = None
    if result is None or "error" in result:
        result = context_from_index(
            index, query, project=project, limit=limit, max_chars=max_chars, lane=lane, state=state
        )
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["index_status"] == "unavailable" else 0
