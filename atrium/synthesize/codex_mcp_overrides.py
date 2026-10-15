"""Codex flags that switch off every MCP server the user config declares."""

import os
import tomllib
from pathlib import Path


def codex_mcp_overrides(codex_home: Path | None = None) -> list[str]:
    """Return ``-c mcp_servers.<name>.enabled=false`` for each configured server.

    Synthesis is pure text-to-JSON and needs no MCP server, and a server marked
    ``required = true`` kills session creation when its startup times out under
    parallel workers. The overrides are derived from the config rather than
    named: disabling a server the config does not declare creates an entry with
    no transport, and codex then refuses to load its config at all (seen
    2026-10-16, after serena left the config).
    """
    home = codex_home or Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    try:
        config = tomllib.loads((home / "config.toml").read_text())
    except FileNotFoundError:
        return []
    overrides: list[str] = []
    for name in config.get("mcp_servers") or {}:
        overrides += ["-c", f"mcp_servers.{name}.enabled=false"]
    return overrides
