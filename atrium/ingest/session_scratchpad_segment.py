"""The encoded project path a session scratchpad directory carries."""

import re

# A per-session scratchpad lives at
# `<temp root>/claude-<uid>/<encoded project path>/<session uuid>/scratchpad`,
# optionally with subdirectories the session made underneath it. The temp root
# is not fixed -- `/private/tmp/claude-501` and `/tmp/claude-0` both appear in
# this archive -- so the parent that is required is the `claude-<uid>` segment
# rather than one literal prefix. Anchoring on it matters: without it any path
# of the shape `<anything>/-<x>/<uuid>/scratchpad` matches, including one inside
# a real project, and that project's records would be re-filed under whatever
# the encoded segment happened to name.
_SCRATCHPAD = re.compile(
    r"^.*/claude-[0-9]+/(?P<segment>-[^/]*)"
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"/scratchpad(?:/.*)?$"
)


def session_scratchpad_segment(workspace: str) -> str | None:
    """Return the encoded project path in ``workspace``, or None if it is not one.

    A scratchpad is a temporary directory belonging to one session, not a
    project, but it is stamped on every record the session produced and so
    became its own workspace in the index. Measured 2026-09-01: 67 such
    workspaces carrying 376 conversations, one workspace per session and
    subdirectory, inflating the project count that made coverage read 2.1% while
    never matching a live ``project_workspace`` -- nothing could ever recall
    them.

    The path is not a dead end, though: the segment before the session uuid is
    the working directory the session ran in, so the conversation can be given
    back to the project it was actually about instead of being thrown away. The
    67 collapse to 19 real projects, 331 conversations remapped and 45 dropped
    because the project they name is no longer on disk.
    """
    found = _SCRATCHPAD.match(workspace)
    return found.group("segment") if found else None
