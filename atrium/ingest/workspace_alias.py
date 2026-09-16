"""One entry of the alias file: where an old workspace name went, and until when."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceAlias:
    """``to`` is the current name; ``until`` (YYYY-MM-DD) bounds the rename.

    Without ``until`` the alias applies to every conversation, which is right
    for a plain rename. A directory that was *reused* needs the date: `p/brain`
    held the wiki until 2026-09-14 and the public engine after, so the engine's
    own sessions were being filed as wiki memory.
    """

    to: str
    until: str | None = None
