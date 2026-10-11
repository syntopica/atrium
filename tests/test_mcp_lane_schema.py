"""The MCP tools show a model which lanes exist, and say why a wrong one fails."""

import asyncio
from typing import get_args

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from atrium.adapters.mcp_server import MCP
from atrium.retrieve.lane import Lane
from atrium.retrieve.search import LANES


def _tools() -> dict:
    return {tool.name: tool for tool in asyncio.run(MCP.list_tools())}


def test_the_lane_type_is_the_lane_list() -> None:
    assert get_args(Lane) == LANES


@pytest.mark.parametrize("name", ["atrium_context", "atrium_search"])
def test_each_tool_lists_the_lanes_in_its_schema(name: str) -> None:
    lane = _tools()[name].input_schema["properties"]["lane"]
    assert lane["enum"] == list(LANES)


def test_an_unknown_lane_comes_back_with_the_reason() -> None:
    with pytest.raises(ToolError, match="lexical"):
        asyncio.run(MCP.call_tool("atrium_context", {"query": "x", "lane": "lexical"}))
