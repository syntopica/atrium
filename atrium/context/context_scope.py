"""Apply provenance and project boundaries before retrieval limits."""


def context_scope(curated: bool, workspace: str | None) -> tuple[str, tuple[str, ...]]:
    """Keep curated notes independent of workspaces and exclude third-party text."""
    if curated:
        return " AND r.role = 'note'", ()
    scope = " AND r.role NOT IN ('source', 'note')"
    if workspace is None:
        return scope, ()
    prefix = workspace.rstrip("/") + "/"
    return scope + " AND (r.workspace = ? OR (r.workspace >= ? AND r.workspace < ?))", (
        workspace,
        prefix,
        prefix[:-1] + "0",
    )
