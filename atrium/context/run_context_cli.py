"""JSON command-line rendering of the shared context contract."""

import json
import time
from pathlib import Path

from atrium.context.context_from_index import context_from_index
from atrium.context.stamp_serving import stamp_serving
from atrium.rerank.cross_encoder import CrossEncoder
from atrium.serve.context_socket_path import context_socket_path
from atrium.serve.request_context_service import request_context_service
from atrium.serve.service_timeout_response import service_timeout_response
from atrium.telemetry.append_query_event import append_query_event

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
    started = time.perf_counter()
    # The service resolves a relative project against its own directory, finds
    # no repository there and fails, so `--project .` -- the form the agent
    # guidance prescribes -- fell back to a cold in-process scan on every call
    # (14 s against 79 ms served, 2026-10-14). The MCP adapter already resolves.
    project = project.expanduser().resolve() if project is not None else None
    request = {
        "index": str(index),
        "query": query,
        "project": str(project) if project is not None else None,
        "limit": limit,
        "max_chars": max_chars,
        "lane": lane,
        "state": str(state),
        "timeout_s": _SERVICE_TIMEOUT_S,
    }
    served_by = "service"
    try:
        result = request_context_service(context_socket_path(state), request, _SERVICE_TIMEOUT_S)
    except TimeoutError:
        result = service_timeout_response(query, project, limit, max_chars, lane, state)
        served_by = "service_timeout"
    except (OSError, ValueError):
        result = None
    if result is None or "error" in result:
        result = context_from_index(
            index,
            query,
            project=project,
            limit=limit,
            max_chars=max_chars,
            lane=lane,
            state=state,
            reranker=CrossEncoder(),
        )
        served_by = "in_process"
    stamp_serving(result, served_by, started)
    append_query_event(state, result, "cli.context")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["index_status"] == "unavailable" else 0
