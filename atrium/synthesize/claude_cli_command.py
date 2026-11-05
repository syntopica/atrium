"""The argv of one headless, tool-free Claude Code CLI call."""

import json
from typing import Any


def claude_cli_command(system_text: str, schema: dict[str, Any], model: str) -> list[str]:
    """Build a `claude -p` call that answers with ``schema`` and touches nothing.

    No tools, no MCP servers, no settings (so no hooks and no plugins), and no
    session file: a persisted session would be archived and synthesized again.
    The account is whatever ``CLAUDE_CONFIG_DIR`` the caller's environment names.
    The stream, unlike the single JSON result, carries the account's usage
    windows (``rate_limit_event``), which is what lets a pass yield before the
    subscription it shares with interactive work is spent.
    """
    return [
        "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--json-schema",
        json.dumps(schema),
        "--tools",
        "",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--no-session-persistence",
        "--system-prompt",
        system_text,
    ]
