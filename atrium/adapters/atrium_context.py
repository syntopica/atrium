"""The `atrium_context` MCP tool."""

import time
from pathlib import Path
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from atrium.adapters.mcp_app import MCP, READ_ONLY
from atrium.adapters.resident_embedder import resident_embedder
from atrium.adapters.resident_reranker import resident_reranker
from atrium.adapters.served_index import INDEX
from atrium.context.context_from_index import context_from_index
from atrium.context.lazy_embedder import LazyEmbedder
from atrium.context.require_workspace import require_workspace
from atrium.context.sanitize_context_response import sanitize_context_response
from atrium.context.stamp_serving import stamp_serving
from atrium.context.validate_request import validate_request
from atrium.retrieve.lane import Lane
from atrium.retrieve.search import LANES
from atrium.serve.context_socket_path import context_socket_path
from atrium.serve.request_context_service import request_context_service
from atrium.serve.service_timeout_response import service_timeout_response
from atrium.state.state_directory import state_directory
from atrium.telemetry.append_lane_event import append_lane_event
from atrium.telemetry.append_query_event import append_query_event

# No hook deadline binds a tool call, so the wait is longer than the CLI's 7 s;
# a service that is listening but stalled is reported, never retried in-process,
# because that would add the slow scan the service exists to avoid.
_SERVICE_TIMEOUT_S = 20.0


@MCP.tool(annotations=READ_ONLY)
def atrium_context(
    query: str,
    project: str | None = None,
    limit: int = 8,
    max_chars: int = 16000,
    lane: Lane = "auto",
) -> dict[str, Any]:
    """Retrieve scoped history, curated notes and one hop of indexed note links.

    Evidence text shares max_chars (1..100000); limit (1..50) caps evidence
    records. Provenance and warnings are additional JSON metadata. History
    requires live verification before asserting present-day operational results.
    """
    started = time.perf_counter()
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
    state = state_directory()
    append_lane_event(state, "mcp.context", lane)
    # Its ValueErrors are the request's own faults (an empty query, a bound out
    # of range, a directory in no repository); the MCP SDK passes on only a
    # ToolError's text, and the model can correct only what it can read. They
    # are checked first so that a stalled service cannot report them as a timeout.
    try:
        validate_request(query, limit, max_chars, lane)
        require_workspace(project)
    except ValueError as error:
        raise ToolError(str(error)) from error
    # The resident service holds the dense matrix and the embedder; without it
    # the dense pass scans the index, which took 115 s unscoped before 75ac8da.
    # A relative project resolves here, never in the service's directory.
    project_path = Path(project).expanduser().resolve() if project is not None else None
    request = {
        "index": str(INDEX),
        "query": query,
        "project": str(project_path) if project_path is not None else None,
        "limit": limit,
        "max_chars": max_chars,
        "lane": lane,
        "state": str(state),
        "timeout_s": _SERVICE_TIMEOUT_S,
    }
    try:
        served = request_context_service(context_socket_path(state), request, _SERVICE_TIMEOUT_S)
    except TimeoutError:
        timed_out = service_timeout_response(query, project_path, limit, max_chars, lane, state)
        answered = stamp_serving(timed_out, "service_timeout", started)
        append_query_event(state, answered, "mcp.context")
        return sanitize_context_response(answered)
    except (OSError, ValueError):
        served = None
    if served is not None and "error" not in served:
        answered = stamp_serving(served, "service", started)
        append_query_event(state, answered, "mcp.context")
        return sanitize_context_response(answered)
    try:
        local = context_from_index(
            INDEX,
            query,
            project=project,
            limit=limit,
            max_chars=max_chars,
            lane=lane,
            state=state,
            embedder=LazyEmbedder(resident_embedder),
            reranker=resident_reranker(),
        )
    except ValueError as error:
        raise ToolError(str(error)) from error
    answered = stamp_serving(local, "in_process", started)
    append_query_event(state, answered, "mcp.context")
    return sanitize_context_response(answered)
