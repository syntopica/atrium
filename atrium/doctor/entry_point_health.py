"""Whether a caller can still reach this memory by the routes it is told to use."""

import os
import socket

from atrium.doctor.finding import Finding
from atrium.doctor.installed_console_scripts import installed_console_scripts
from atrium.doctor.locate_command import locate_command
from atrium.doctor.login_search_path import login_search_path
from atrium.doctor.mcp_extra_requirements import mcp_extra_requirements
from atrium.doctor.mcp_route_gaps import MCP_SCRIPT, mcp_route_gaps

# The two documented ways in: the CLI the agent guidance prescribes
# (`atrium search "<question>" --project .`) and the console script both
# `.claude.json` files spawn as `uv run --extra mcp --directory ~/p/atrium
# atrium-mcp`. The index was all-green for weeks while the CLI existed only
# inside `~/p/atrium/.venv`, so every session that followed the guidance got
# `command not found` and improvised instead -- a live memory nobody could ask.
COMMAND = "atrium"


def entry_point_health(
    search_path: str | None = None,
    hostname: str | None = None,
    scripts: dict[str, str] | None = None,
    requirements: list[str] | None = None,
) -> Finding:
    """Report whether a login shell would find the CLI and the MCP route is intact.

    The PATH examined is not the one this process inherited. Every documented
    route to the doctor runs it under `uv run --project ~/p/atrium`, which
    prepends the venv's `bin` -- where the console scripts exist because
    installing the project put them there. Asked of that PATH the check is
    green in precisely the state it exists to catch, so the venv's script
    directory is removed first and the question is put to what remains.

    The MCP server is not spawned. It is a stdio server that blocks until its
    client speaks, and it runs in a different environment from the doctor (the
    `mcp` extra), so starting one proves nothing this process could report.
    What is checked is the part of `uv run --extra mcp ... atrium-mcp` that
    lives in the installed metadata and does fail in practice: the console
    script is declared, the module it names resolves, and the `mcp` extra
    survived into the distribution -- uv refuses an extra it cannot find. The
    summary says so, so a green line is not read as proof the host can spawn it.
    """
    machine = socket.gethostname() if hostname is None else hostname
    path = login_search_path(os.environ.get("PATH", "")) if search_path is None else search_path
    missing: list[str] = []
    detail: dict[str, object] = {"hostname": machine, "search_path": path}

    lookup = locate_command(COMMAND, path)
    if lookup.shadows:
        detail["shadowed_by"] = list(lookup.shadows)
    if lookup.command is None:
        missing.extend(lookup.shadows)
        if not lookup.shadows:
            missing.append(f"{COMMAND} is not on PATH a login shell would use")
    else:
        detail["command"] = str(lookup.command)

    declared = installed_console_scripts() if scripts is None else scripts
    extra = mcp_extra_requirements() if requirements is None else requirements
    detail["mcp_entry_point"] = declared.get(MCP_SCRIPT)
    detail["mcp_extra"] = extra
    missing.extend(mcp_route_gaps(declared, extra))

    if missing:
        return Finding(
            check="entrypoints",
            severity="broken",
            summary=f"{machine}: " + "; ".join(missing),
            detail={**detail, "missing": missing},
        )
    if lookup.shadows:
        return Finding(
            check="entrypoints",
            severity="warn",
            summary=(
                f"{machine}: {COMMAND} runs from {lookup.command}, but "
                + "; ".join(lookup.shadows)
                + f" comes first on PATH; {MCP_SCRIPT} is declared, not started"
            ),
            detail=detail,
        )
    return Finding(
        check="entrypoints",
        severity="ok",
        summary=(
            f"{machine}: {COMMAND} resolves at {lookup.command}; "
            f"{MCP_SCRIPT} is declared, not started"
        ),
        detail=detail,
    )
