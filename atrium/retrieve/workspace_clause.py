"""The SQL that narrows a lane to one project, shared by every lane."""

# A path is not a pattern. `_` and `%` are LIKE metacharacters and 2,585
# distinct workspaces in this corpus contain `_`, so LIKE would quietly pull a
# neighbouring project's records in. substr compares the prefix literally and
# has nothing to escape.
CONDITION = "(r.workspace = ? OR substr(r.workspace, 1, length(?) + 1) = ? || '/')"


def workspace_clause(workspace: str | None) -> tuple[str, tuple[str, ...]]:
    """Return the ``AND`` fragment and its parameters for ``workspace``.

    Empty when unscoped, so an unscoped search is the same query it always was
    rather than one carrying a condition that is always true.

    The narrowing belongs inside each lane, before its ``LIMIT`` and before
    fusion. Filtering the returned hits instead would ask for the top N of
    everything and then throw most away, so a project with few records would
    come back empty while its matches sat just outside the window.
    """
    if workspace is None:
        return "", ()
    return f" AND {CONDITION}", (workspace, workspace, workspace)
