"""What the `mcp` extra of this distribution says it needs."""

from importlib.metadata import requires

# `importlib.metadata.requires` returns the raw metadata lines, extras included
# as an environment marker: `mcp>=2.1; extra == "mcp"`. Matching the marker
# textually avoids a `packaging` dependency the project does not otherwise have.
EXTRA = "mcp"
MARKERS = (f'extra == "{EXTRA}"', f"extra == '{EXTRA}'")


def mcp_extra_requirements(distribution: str = "atrium") -> list[str]:
    """Return the requirement strings ``distribution`` declares for the `mcp` extra.

    An empty list is a real failure, not an absence of information: both
    `.claude.json` files spawn the server as `uv run --extra mcp --directory
    ~/p/mem atrium-mcp`, and uv refuses an extra the installed metadata does
    not declare. So the extra having survived into the installed distribution
    is the part of that command line this process can honestly check.
    """
    declared = requires(distribution) or []
    return [
        line.split(";", 1)[0].strip()
        for line in declared
        if any(form in line.partition(";")[2] for form in MARKERS)
    ]
