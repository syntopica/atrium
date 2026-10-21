"""Resolve the instance path already configured for Codex's Atrium server."""

import os
from pathlib import Path


def instance_data() -> str:
    """Prefer the hook environment, then the existing MCP environment."""
    if os.environ.get("SYNTOPICA_DATA"):
        return os.environ["SYNTOPICA_DATA"]
    try:
        import tomllib

        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        with (home / "config.toml").open("rb") as handle:
            configuration = tomllib.load(handle)
        return str(
            configuration.get("mcp_servers", {})
            .get("atrium", {})
            .get("env", {})
            .get("SYNTOPICA_DATA", "")
        )
    except (OSError, ValueError, ImportError):
        return ""
