"""Whether a stored workspace belongs to one project."""


def workspace_matches(workspace: str | None, project: str) -> bool:
    """True when ``workspace`` is ``project`` or sits underneath it.

    The Python twin of the SQL in ``workspace_scope``: the project root itself,
    or anything below it, and nothing that merely shares a name prefix --
    `[HOME]/p/project-after-enrichment-backfill` is not part of `[HOME]/p/project-after`, and
    treating it as such would quietly fold a neighbouring project's history in.
    """
    if not workspace:
        return False
    return workspace == project or workspace.startswith(project.rstrip("/") + "/")
