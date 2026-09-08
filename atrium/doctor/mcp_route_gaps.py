"""What is broken about the route the MCP host uses, without spawning the server."""

from importlib.util import find_spec

# Both `.claude.json` files spawn the server as `uv run --extra mcp --directory
# ~/p/atrium atrium-mcp`. Every part of that line this process can honestly
# answer for lives in the installed metadata; the spawn itself cannot be
# checked here, because the server blocks until its client speaks and runs in
# an environment (the `mcp` extra) the doctor is not in.
MCP_SCRIPT = "atrium-mcp"


def mcp_route_gaps(scripts: dict[str, str], requirements: list[str]) -> list[str]:
    """Return each reason the documented MCP spawn would fail before it starts.

    Three things fail in practice and none of them need the protocol SDK: the
    console script never got installed, the module it names moved, and the
    `mcp` extra did not survive into the distribution -- uv refuses an extra
    the installed metadata does not declare. Whether `mcp>=2.1` is *resolvable*
    is deliberately not asserted: the doctor runs without that extra, so its
    absence here would be evidence about the doctor's environment, not the
    host's, and reporting it would make a healthy machine red.
    """
    gaps: list[str] = []
    target = scripts.get(MCP_SCRIPT)
    if target is None:
        gaps.append(f"{MCP_SCRIPT} is not an installed console script")
    elif find_spec(target.split(":", 1)[0]) is None:
        gaps.append(f"{MCP_SCRIPT} points at {target.split(':', 1)[0]}, which does not resolve")
    if not requirements:
        gaps.append("the mcp extra declares no requirements, so --extra mcp would fail")
    return gaps
