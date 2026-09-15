"""Exercise a fresh MCP subprocess rather than invoking its Python adapter directly."""

import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def context_protocol_exchange(env: dict[str, str], project: str) -> dict:
    """Return context and legacy search from a newly initialized MCP server."""
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "atrium.adapters.mcp_server"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
    )
    async with (
        stdio_client(server) as (reader, writer),
        ClientSession(reader, writer, read_timeout_seconds=20) as session,
    ):
        await session.initialize()
        listing = await session.list_tools()
        tool = next(tool for tool in listing.tools if tool.name == "atrium_context")
        result = await session.call_tool(
            "atrium_context",
            {"query": "Atlas mail", "project": project, "lane": "words", "max_chars": 4000},
        )
        legacy = await session.call_tool(
            "atrium_search",
            {"query": "DELIVERED_WITHOUT_EVIDENCE", "project": project, "lane": "words"},
        )
        invalid = await session.call_tool("atrium_context", {"query": "Atlas", "limit": 0})
        return {"context": result, "legacy": legacy, "invalid": invalid, "tool": tool}
