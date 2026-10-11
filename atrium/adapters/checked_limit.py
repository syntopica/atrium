"""Validation of a tool's requested result count."""

from mcp.server.mcpserver.exceptions import ToolError

from atrium.adapters.max_limit import MAX_LIMIT


def checked_limit(limit: int) -> int:
    """Return ``limit`` capped at ``MAX_LIMIT``; raise when it is below one.

    A ``ToolError``, since the MCP SDK hands the model only that text: any other
    exception reaches it as a bare "Error executing tool", with nothing to fix.
    """
    if limit < 1:
        raise ToolError(f"limit must be at least 1, got {limit}")
    return min(limit, MAX_LIMIT)
