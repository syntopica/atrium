"""The MCP server object every atrium tool registers on."""

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

MCP = MCPServer("atrium")

# Both tools open the index read-only and neither has anything to undo, which
# is what lets a host auto-approve them. Declaring it is not decoration: a host
# that has to assume a tool writes will stop and ask before every recall.
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
