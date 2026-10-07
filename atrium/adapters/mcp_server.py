"""MCP adapter: atrium's retrieval, served to an agent over stdio."""

from atrium.adapters.atrium_context import atrium_context
from atrium.adapters.atrium_recall import atrium_recall
from atrium.adapters.atrium_search import atrium_search
from atrium.adapters.mcp_app import MCP

# Importing a tool module registers it on MCP. Naming them here keeps that
# registration explicit, in the order the host lists them.
TOOLS = (atrium_search, atrium_recall, atrium_context)


def main() -> None:
    """Serve over stdio until the host closes the pipe."""
    MCP.run()


if __name__ == "__main__":
    main()
